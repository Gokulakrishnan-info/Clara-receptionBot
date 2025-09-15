import os
import time
import threading
from typing import Dict, Optional

import cv2
import pandas as pd

from livekit.agents import function_tool, RunContext
import speech_recognition as sr

from Modules import config
from Modules.state import employee_access
import Modules.state as state_module
from Face.recognize_wrapper import Recognizer, draw_detections


def wait_for_wakeword(wake_phrase: str = "hey clara") -> None:
    # Simple mic-based wake word listener using speech_recognition
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print(f"Listening for wake word: '{wake_phrase}' ... (Ctrl+C to cancel)")
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=4)
                text = recognizer.recognize_google(audio).lower()
                if wake_phrase.lower() in text:
                    print("Wake word detected")
                    return
            except sr.UnknownValueError:
                continue
            except KeyboardInterrupt:
                break


def load_employee_db(csv_path: str) -> Dict[str, Dict[str, str]]:
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    # Expect columns: EmployeeID, Name, Email, ... adapt if needed
    id_col = "EmployeeID" if "EmployeeID" in df.columns else "id"
    result: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        emp_id = str(row[id_col]).strip()
        result[emp_id] = {k: str(v) for k, v in row.items()}
    return result


class FaceGreetingService:
    def __init__(self, embeddings_path: str, employee_csv: str, threshold: float = 0.65, cooldown_s: int = 20, camera_index: int = 0):
        try:
            self.recognizer = Recognizer(embeddings_path=embeddings_path, threshold=threshold)
            self.employee_db = load_employee_db(employee_csv)
        except Exception as e:
            print(f"Error initializing FaceGreetingService: {e}")
            self.recognizer = None
            self.employee_db = {}
        self.cooldown_s = cooldown_s
        self.camera_index = camera_index
        self._last_greet_time: Dict[str, float] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_unknown_time: float = 0.0
        self._initial_delay: float = 15.0  # Wait 15 seconds before prompting unknown users

    def start(self, on_greet, on_prompt=None):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._initial_delay = time.time() + 15.0  # Set initial delay from now
        self._thread = threading.Thread(target=self._run, args=(on_greet, on_prompt), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background service and cleanup resources."""
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        # Cleanup camera resources
        if hasattr(self, '_cap') and self._cap is not None:
            self._cap.release()
            cv2.destroyAllWindows()

    def _run(self, on_greet, on_prompt=None):
        print(f"[FaceGreetingService] Opening camera index {self.camera_index} ...")
        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            print(f"Error: Camera index {self.camera_index} could not be opened.")
        window_name = "Clara Face Recognition"
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 800, 600)
        except Exception:
            pass
        print("Face recognition started. Press 'q' window focus to stop.")
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    print("[FaceGreetingService] Failed to read frame from camera.")
                    break
                detections = self.recognizer.recognize_frame(frame)

                # draw and show
                out = draw_detections(frame.copy(), detections)
                cv2.imshow(window_name, out)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                # greet highest-confidence recognized emp once per cooldown
                recognized = [d for d in detections if d['emp_id'] != 'Unknown']
                if recognized:
                    top = max(recognized, key=lambda d: d['conf'])
                    emp_id = top['emp_id']
                    now = time.time()
                    last = self._last_greet_time.get(emp_id, 0)
                    if now - last >= self.cooldown_s:
                        self._last_greet_time[emp_id] = now
                        emp = self.employee_db.get(emp_id)
                        if emp:
                            on_greet(emp)
                        else:
                            print(f"Recognized {emp_id}, but not found in CSV")
                else:
                    # Unknown users: prompt occasionally via LiveKit (no local TTS)
                    # But wait for initial delay to avoid conflicting with initial decision
                    now = time.time()
                    if now - self._last_unknown_time >= 10 and now >= self._initial_delay:
                        self._last_unknown_time = now
                        if on_prompt:
                            on_prompt("I don't recognize you. Are you a candidate or a visitor?")
        finally:
            cap.release()
            cv2.destroyAllWindows()


service_singleton: Optional[FaceGreetingService] = None


def reset_face_recognition_state():
    """Reset the face recognition state for a new session."""
    import Modules.state as state_module
    state_module.face_recognition_completed = False


@function_tool()
async def new_user_detected() -> str:
    """Detect when a user says goodbye and reset all state for next user."""
    print("DEBUG: User said goodbye, resetting all state")
    print(f"DEBUG: Before reset - face_recognition_completed: {state_module.face_recognition_completed}")
    print(f"DEBUG: Before reset - current_employee_id: {state_module.current_employee_id}")
    
    # Reset all state for new user
    state_module.face_recognition_completed = False
    state_module.current_employee_id = None
    # Clear all employee access
    state_module.employee_access.clear()
    
    print(f"DEBUG: After reset - face_recognition_completed: {state_module.face_recognition_completed}")
    print(f"DEBUG: After reset - current_employee_id: {state_module.current_employee_id}")
    print("DEBUG: All state reset - ready for next user")
    return "Goodbye! Have a great day! Please say 'hey clara' when the next person arrives."


def _first_decision(embeddings_path: str, employee_csv: str, cam_index: int, threshold: float, min_stable_frames: int = 3, timeout_s: int = 8):
    """One-time face recognition decision with camera display.
    Returns (message: str | None)."""
    recog = Recognizer(embeddings_path=embeddings_path, threshold=threshold)
    employees = load_employee_db(employee_csv)

    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        return "❌ Camera could not be opened. Check VR_CAMERA_INDEX."

    # Create camera window
    window_name = "Clara Face Recognition"
    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
    except Exception:
        pass

    stable_count: Dict[str, int] = {}
    start = time.time()
    face_detected = False
    
    try:
        while time.time() - start < timeout_s:
            ok, frame = cap.read()
            if not ok:
                break
            
            # Detect faces and draw bounding boxes
            dets = recog.recognize_frame(frame)
            out = draw_detections(frame.copy(), dets)
            cv2.imshow(window_name, out)
            
            # Check for 'q' key to quit early
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Check if any face is detected (even unknown)
            if dets:
                face_detected = True
                print(f"DEBUG: Face detected: {dets}")
                
                # Check all detections, not just recognized ones
                for det in dets:
                    emp_id = det["emp_id"]
                    conf = det["conf"]
                    print(f"DEBUG: Detection - ID: {emp_id}, Confidence: {conf:.3f}, Threshold: {threshold}")
                
                # take top recognized
                recogs = [d for d in dets if d["emp_id"] != "Unknown"]
                if recogs:
                    top = max(recogs, key=lambda d: d["conf"])
                    emp_id = top["emp_id"]
                    print(f"DEBUG: Top recognized employee: {emp_id} with confidence {top['conf']}")
                    stable_count[emp_id] = stable_count.get(emp_id, 0) + 1
                    print(f"DEBUG: Stable count for {emp_id}: {stable_count[emp_id]}/{min_stable_frames}")
                    if stable_count[emp_id] >= min_stable_frames:
                        emp = employees.get(emp_id)
                        print(f"DEBUG: Employee data for {emp_id}: {emp}")
                        if emp:
                            name = emp.get("Name") or emp.get("Employee Name") or emp_id
                            print(f"DEBUG: Found employee name: {name}")
                            # Mark access granted via face recognition
                            employee_access[emp_id]["granted"] = True
                            employee_access[emp_id]["source"] = "face"
                            # Set current employee ID for easy access
                            state_module.current_employee_id = emp_id
                            print(f"DEBUG: Set current_employee_id to {emp_id}")
                            return f"Hello {name}! Welcome back! How can I assist you today?"
                        else:
                            print(f"DEBUG: Employee {emp_id} not found in database")
                            return f"Recognized {emp_id}, but I couldn't find your details. Are you a candidate or a visitor?"
                else:
                    # Unknown face detected - wait a bit for stability then return
                    print("DEBUG: Unknown face detected, returning message")
                    time.sleep(1)  # Give a moment for stable detection
                    return "Hello! I don't recognize you. Are you a candidate or a visitor?"
        
        # timeout -> check if face was detected
        print(f"DEBUG: Timeout reached, face_detected={face_detected}")
        if face_detected:
            return "Hello! I don't recognize you. Are you a candidate or a visitor?"
        else:
            # No face detected - still ask the question as if they're there
            print("DEBUG: No face detected, but asking question anyway")
            return "Hello! I don't recognize you. Are you a candidate or a visitor?"
    except Exception as e:
        print(f"ERROR in _first_decision: {e}")
        import traceback
        traceback.print_exc()
        return "Hello! I don't recognize you. Are you a candidate or a visitor?"
    finally:
        cap.release()
        cv2.destroyAllWindows()


@function_tool()
async def retry_face_recognition(
    context: RunContext,
    embeddings_path: Optional[str] = None,
    threshold: float = 0.6,
    min_stable_frames: int = 2,
    timeout_s: int = 8,
) -> str:
    """
    Retry face recognition for someone who claims to be an employee but wasn't recognized initially.
    This gives them another chance to be identified via face recognition.
    """
    print("Retrying face recognition for claimed employee...")
    try:
        # Use default embeddings path if not provided
        if embeddings_path is None:
            embeddings_path = os.getenv("VR_FACE_EMBEDDINGS", "face_embeddings.pkl")
        
        # Load employee database
        employee_csv = os.getenv("VR_EMPLOYEE_CSV", "dummy-data/employee_details.csv")
        employee_db = load_employee_db(employee_csv)
        if not employee_db:
            return "❌ Could not load employee database. Please try manual verification."
        
        # Load face recognition models
        recognizer = Recognizer(embeddings_path)
        
        # Open camera
        camera_index = int(os.getenv("VR_CAMERA_INDEX", "0"))
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return f"❌ Could not open camera {camera_index}. Please check camera connection."
        
        print(f"Retry face recognition: Opening camera index {camera_index}")
        
        # Try recognition for a shorter time
        start_time = time.time()
        last_recognition = None
        stable_count = 0
        
        while time.time() - start_time < timeout_s:
            ret, frame = cap.read()
            if not ret:
                continue
                
            # Resize frame for better performance
            frame = cv2.resize(frame, (640, 480))
            
            # Try to recognize faces
            try:
                results = recognizer.recognize_frame(frame)
                
                if results:
                    # Use the first (most confident) result
                    result = results[0]
                    emp_id = result['emp_id']
                    confidence = result['conf']
                    
                    # Check if this is a new recognition or same as before
                    if last_recognition != emp_id:
                        last_recognition = emp_id
                        stable_count = 0
                    else:
                        stable_count += 1
                    
                    # If we have stable recognition, process it
                    if stable_count >= min_stable_frames:
                        cap.release()
                        
                        # Look up employee details
                        emp = employee_db.get(emp_id)
                        if emp:
                            name = emp.get("Name") or emp.get("Employee Name") or emp_id
                            # Mark access granted via face recognition
                            employee_access[emp_id]["granted"] = True
                            employee_access[emp_id]["source"] = "face"
                            
                            return f"Great! I recognize you now, {name}! You're all set. How can I assist you today?"
                        else:
                            return f"Recognized {emp_id}, but I couldn't find your details. Are you a candidate or a visitor?"
                
            except Exception as e:
                print(f"Recognition error: {e}")
                continue
        
        cap.release()
        return (
            "I still couldn't recognize you. Let's try manual verification instead. "
            "Please provide your employee ID and name for verification."
        )
        
    except Exception as e:
        print(f"Retry face recognition error: {e}")
        return f"❌ Error during retry face recognition: {str(e)}"


@function_tool()
async def start_face_greeting(
    context: RunContext,
    embeddings_path: Optional[str] = None,
    threshold: float = 0.6,
    wait_for_wake: bool = True,
    min_stable_frames: int = 2,
    timeout_s: int = 8,
) -> str:
    """One-time face recognition after wake word - no continuous background service."""
    
    # Check if face recognition has already been completed in this session
    print(f"DEBUG: start_face_greeting called - face_recognition_completed: {state_module.face_recognition_completed}")
    print(f"DEBUG: start_face_greeting called - current_employee_id: {state_module.current_employee_id}")
    
    if state_module.face_recognition_completed:
        print("DEBUG: Face recognition already completed, returning early")
        return "You're already authenticated. How can I assist you today? If you'd like me to re-check, just say 'retry face recognition'."
    
    # Resolve embeddings path
    print("Starting face recognition...")
    if not embeddings_path:
        embeddings_path = os.getenv("VR_FACE_EMBEDDINGS")
    if not embeddings_path or not os.path.exists(embeddings_path):
        err = "❌ Face embeddings path not set or not found. Set VR_FACE_EMBEDDINGS or pass embeddings_path."
        print(err)
        return err

    # Wait for wake word before starting camera (can be bypassed)
    bypass_env = os.getenv("BYPASS_WAKEWORD", "0") == "1"
    if wait_for_wake and not bypass_env:
        print("Listening for wake word 'hey clara'...")
        wait_for_wakeword("hey clara")

    # Make a one-time face recognition decision
    cam_index = int(os.getenv("VR_CAMERA_INDEX", "0"))
    print(f"Starting one-time face recognition for {timeout_s} seconds...")
    
    try:
        # Run face recognition in a thread to avoid blocking the async function
        import asyncio
        import concurrent.futures
        
        def run_face_recognition():
            return _first_decision(
                embeddings_path=embeddings_path,
                employee_csv=config.EMPLOYEE_CSV,
                cam_index=cam_index,
                threshold=threshold,
                min_stable_frames=min_stable_frames,
                timeout_s=timeout_s,
            )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            msg = await loop.run_in_executor(executor, run_face_recognition)
        
        print("Face recognition completed. Camera closed.")
        print(f"DEBUG: _first_decision returned: {msg}")
        
        # Ensure we always return a message
        if msg is None:
            msg = "UNKNOWN: Hello! I don't recognize you. Are you a candidate or a visitor?"
            print(f"DEBUG: msg was None, using fallback: {msg}")
        
        # Mark face recognition as completed
        state_module.face_recognition_completed = True
        
        # Log the final message being returned
        print(f"DEBUG: Final message being returned to agent: {msg}")
        
        # Return the result - Clara will speak this
        return msg
        
    except Exception as e:
        print(f"ERROR in start_face_greeting: {e}")
        import traceback
        traceback.print_exc()
        # Mark face recognition as completed even on error
        state_module.face_recognition_completed = True
        # Return a fallback message
        return "UNKNOWN: Hello! I don't recognize you. Are you a candidate or a visitor?"


