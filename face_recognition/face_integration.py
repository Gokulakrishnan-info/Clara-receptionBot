import os
import time
import threading
import logging
from typing import Dict, Optional

import cv2
import pandas as pd

from livekit.agents import function_tool, RunContext
import speech_recognition as sr

from Modules import config
from Modules.state import employee_access, otp_sessions
from Modules.send_email import send_email_smtp
import Modules.state as state_module
from .recognize_wrapper import Recognizer, draw_detections
import numpy as np
import pickle
try:
    import insightface
except Exception:
    insightface = None


logger = logging.getLogger(__name__)

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
                    logger.info("Wake word detected: %s", text)
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
async def new_user_detected(reason: str = "goodbye") -> str:
    """Reset all runtime state for a fresh interaction.

    reason: "wake" when triggered by the wake word ("hey clara"),
            "goodbye" when ending a session,
            anything else will default to a neutral reset line.
    """
    print(f"DEBUG: Reset triggered, reason='{reason}'")
    print(f"DEBUG: Before reset - face_recognition_completed: {state_module.face_recognition_completed}")
    print(f"DEBUG: Before reset - current_employee_id: {state_module.current_employee_id}")
    
    # Reset all state for new user
    state_module.face_recognition_completed = False
    state_module.current_employee_id = None
    # Clear selected role if present
    try:
        state_module.selected_role = None
    except AttributeError:
        # older state modules may not have this; ignore
        pass
    # Clear all employee access
    state_module.employee_access.clear()
    
    print(f"DEBUG: After reset - face_recognition_completed: {state_module.face_recognition_completed}")
    print(f"DEBUG: After reset - current_employee_id: {state_module.current_employee_id}")
    print("DEBUG: All state reset - ready for next user")
    
    if reason == "wake":
        return "Reset complete. Are you an employee, a candidate, or a visitor?"
    if reason == "goodbye":
        return "Goodbye! Have a great day! Please say 'hey clara' when the next person arrives."
    return "Ready for the next person. Are you an employee, a candidate, or a visitor?"


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
                            empid_norm_key = str(emp_id).strip().upper()
                            employee_access[empid_norm_key]["granted"] = True
                            employee_access[empid_norm_key]["source"] = "face"
                            # Set current employee ID for easy access
                            state_module.current_employee_id = empid_norm_key
                            print(f"DEBUG: Set current_employee_id to {emp_id}")
                            return f"SUCCESS: Hello {name}! Welcome back! How can I assist you today? (Employee verified via face recognition)"
                        else:
                            print(f"DEBUG: Employee {emp_id} not found in database")
                            return f"UNKNOWN: I don't recognize you. Can we register your face?"
                else:
                    # Unknown face detected - wait a bit for stability then return
                    print("DEBUG: Unknown face detected, returning message")
                    time.sleep(1)  # Give a moment for stable detection
                    return "UNKNOWN: I don't recognize you. Can we register your face?"
        
        # timeout -> check if face was detected
        print(f"DEBUG: Timeout reached, face_detected={face_detected}")
        if face_detected:
            return "UNKNOWN: I don't recognize you. Can we register your face?"
        else:
            # No face detected - still ask the question as if they're there
            print("DEBUG: No face detected, but asking question anyway")
            return "UNKNOWN: I don't recognize you. Can we register your face?"
    except Exception as e:
        print(f"ERROR in _first_decision: {e}")
        import traceback
        traceback.print_exc()
        return "UNKNOWN: I don't recognize you. Can we register your face?"
    finally:
        cap.release()
        cv2.destroyAllWindows()


def _append_embedding_for_employee(employee_id: str, embeddings_file: str, camera_index: int = 0, frames_to_collect: int = 5) -> str:
    """Capture embeddings from camera and append to the pickle for a specific employee ID."""
    if insightface is None:
        return "❌ Enrollment requires insightface. Please ensure it is installed."

    app = insightface.app.FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return f"❌ Could not open camera {camera_index} for enrollment."

    collected: list[np.ndarray] = []
    best_face_frame = None
    try:
        # Brief warm-up and countdown overlay
        countdown_secs = 3
        end_warmup = time.time() + countdown_secs
        while time.time() < end_warmup:
            ok, frame = cap.read()
            if not ok:
                continue
            msg = f"Look at the camera… {int(end_warmup - time.time())+1}"
            try:
                cv2.putText(frame, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.imshow("Clara Face Registration", frame)
                cv2.waitKey(1)
            except Exception:
                pass

        start_time = time.time()
        capture_timeout = 10
        while len(collected) < frames_to_collect and time.time() - start_time < capture_timeout:
            ok, frame = cap.read()
            if not ok:
                continue
            try:
                cv2.putText(frame, "Capturing… Please keep looking at the camera", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow("Clara Face Registration", frame)
                cv2.waitKey(1)
            except Exception:
                pass

            faces = app.get(frame)
            if not faces:
                continue
            # keep a copy of a frame with a detected face to save image later
            if best_face_frame is None:
                best_face_frame = frame.copy()
            emb = faces[0].embedding.astype(np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            collected.append(emb)
        if not collected:
            return "❌ Unable to capture a face for enrollment. Please try again."
        avg_emb = np.mean(collected, axis=0).astype(np.float32)
        norm = np.linalg.norm(avg_emb)
        if norm > 0:
            avg_emb = avg_emb / norm

        # Load existing
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, "rb") as f:
                    db = pickle.load(f)
            except Exception:
                db = {}
        else:
            db = {}

        # Ensure list container
        if employee_id not in db:
            db[employee_id] = []
        db[employee_id].append(avg_emb)

        with open(embeddings_file, "wb") as f:
            pickle.dump(db, f)

        # Also save the captured face image if not present
        photos_dir = os.getenv("VR_EMP_PHOTOS", os.path.join("Employee", "EMP_Photos"))
        os.makedirs(photos_dir, exist_ok=True)
        img_path = os.path.join(photos_dir, f"{employee_id}.jpg")
        if best_face_frame is not None and not os.path.exists(img_path):
            try:
                cv2.imwrite(img_path, best_face_frame)
            except Exception:
                pass

        # Grant access now that the face is enrolled
        empid_norm_key = str(employee_id).strip().upper()
        employee_access[empid_norm_key]["granted"] = True
        employee_access[empid_norm_key]["source"] = "face"
        state_module.current_employee_id = empid_norm_key
        return f"✅ Face registered for {employee_id}. You're all set."
    finally:
        cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


@function_tool()
async def register_employee_face(
    context: RunContext,
    employee_id: str,
    frames_to_collect: int = 5,
    embeddings_path: str | None = None,
) -> str:
    """After OTP validation, capture face and append to embeddings for this employee ID."""
    if not employee_id:
        return "❌ employee_id is required to register face."
    if embeddings_path is None:
        embeddings_path = os.getenv("VR_FACE_EMBEDDINGS", "face_embeddings.pkl")
    camera_index = int(os.getenv("VR_CAMERA_INDEX", "0"))
    return _append_embedding_for_employee(employee_id.strip(), embeddings_path, camera_index, frames_to_collect)


@function_tool()
async def request_employee_face_registration(
    context: RunContext,
    employee_id: str,
) -> str:
    """Start registration: check if photo exists, validate ID in DB, send OTP to email."""
    if not employee_id:
        return "❌ Please provide a valid Employee ID."
    emp_id = employee_id.strip()

    # 1) Check if image already exists for this Employee ID
    photos_dir = os.getenv("VR_EMP_PHOTOS", os.path.join("Employee", "EMP_Photos"))
    img_jpg = os.path.join(photos_dir, f"{emp_id}.jpg")
    img_png = os.path.join(photos_dir, f"{emp_id}.png")
    if os.path.exists(img_jpg) or os.path.exists(img_png):
        return (
            "⚠️ An image for this Employee ID already exists in the database. "
            "Please recheck and provide the correct Employee ID."
        )

    # 2) Validate Employee ID in DB and get email
    employee_csv = os.getenv("VR_EMPLOYEE_CSV", getattr(config, "EMPLOYEE_CSV", "data/employee_details.csv"))
    try:
        df = pd.read_csv(employee_csv, dtype=str).fillna("")
        df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()
        row = df[df["EmployeeID_norm"] == emp_id.upper()]
        if row.empty:
            return "❌ Employee ID not found in database. Please recheck."
        email = str(row.iloc[0]["Email"]).strip()
        if not email:
            return "❌ No email on record for this Employee ID."
    except Exception as e:
        return f"❌ Could not read employee database: {e}"

    # 3) Send OTP to email
    import random
    otp = str(random.randint(100000, 999999))
    otp_sessions[email] = {"otp": otp, "verified": False, "attempts": 0, "employee_id": emp_id}
    try:
        send_email_smtp([email], "Face Registration OTP", f"Your OTP for face registration is: {otp}")
    except Exception as e:
        return f"❌ Error sending OTP email: {e}"

    return f"✅ I sent a verification code to {email}. Please tell me the OTP to continue."

@function_tool()
async def complete_employee_face_registration(
    context: RunContext,
    employee_id: str,
    otp: str,
) -> str:
    """Verify OTP, then capture and save face embedding. 
       Will not overwrite existing employee image."""
    if not employee_id or not otp:
        return "❌ Employee ID and OTP are required."

    emp_id = employee_id.strip()

    # 1) Check if image already exists
    photos_dir = os.getenv("VR_EMP_PHOTOS", os.path.join("Employee", "EMP_Photos"))
    img_jpg = os.path.join(photos_dir, f"{emp_id}.jpg")
    img_png = os.path.join(photos_dir, f"{emp_id}.png")
    if os.path.exists(img_jpg) or os.path.exists(img_png):
        return (
            "⚠️ An image for this Employee ID already exists in the database. "
            "Please recheck and provide the correct Employee ID."
        )

    # 2) Verify OTP
    session = None
    for email, data in otp_sessions.items():
        if data.get("employee_id") == emp_id:
            session = (email, data)
            break
    if not session:
        return "❌ No OTP session found. Please restart the registration."
    
    email, data = session
    if otp != data.get("otp"):
        data["attempts"] += 1
        if data["attempts"] >= 3:
            otp_sessions.pop(email, None)
            return "❌ Too many failed attempts. Please restart the registration."
        return "❌ Invalid OTP. Please try again."

    # Mark verified
    data["verified"] = True

    # 3) Capture and save image
    photos_dir = os.getenv("VR_EMP_PHOTOS", os.path.join("Employee", "EMP_Photos"))
    os.makedirs(photos_dir, exist_ok=True)
    img_path = os.path.join(photos_dir, f"{emp_id}.jpg")

    camera_index = int(os.getenv("VR_CAMERA_INDEX", "0"))
    if insightface is None:
        return "❌ insightface not available to generate embeddings."
    app = insightface.app.FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    # Try multiple attempts to capture a usable face
    max_attempts = 3
    found_face = None
    captured_frame = None

    for attempt in range(1, max_attempts + 1):
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return f"❌ Could not access camera index {camera_index}."

        # brief on-screen cue
        end_time = time.time() + 2
        while time.time() < end_time:
            ok, preview = cap.read()
            if not ok:
                continue
            try:
                cv2.putText(preview, f"Attempt {attempt}/{max_attempts}: Please face the camera", (18, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.imshow("Clara Registration", preview)
                cv2.waitKey(1)
            except Exception:
                pass

        # capture a frame and check for a face
        ret, frame = cap.read()
        cap.release()
        if not ret:
            continue

        faces = app.get(frame)
        if faces:
            found_face = faces[0]
            captured_frame = frame
            break
        else:
            # Inform the user to adjust and we will retry (the agent will speak the return string)
            if attempt < max_attempts:
                try:
                    cv2.putText(frame, "No face detected. Adjust lighting/positioning…", (18, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.imshow("Clara Registration", frame)
                    cv2.waitKey(800)
                except Exception:
                    pass

    if not found_face or captured_frame is None:
        return "❌ I couldn't detect your face. Please face the camera with good lighting and say 'yes' to try again."

    # Save image
    try:
        cv2.imwrite(img_path, captured_frame)
    except Exception:
        return "❌ Failed to save captured image."

    # Build normalized embedding
    emb = found_face.embedding.astype(np.float32)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    embeddings_file = os.getenv("VR_FACE_EMBEDDINGS", "face_embeddings.pkl")
    if os.path.exists(embeddings_file):
        try:
            with open(embeddings_file, "rb") as f:
                db = pickle.load(f)
        except Exception:
            db = {}
    else:
        db = {}

    if emp_id not in db:
        db[emp_id] = []
    db[emp_id].append(emb)

    try:
        with open(embeddings_file, "wb") as f:
            pickle.dump(db, f)
    except Exception:
        return "❌ Failed to update embeddings file."

    # Grant access after registration
    employee_access[emp_id]["granted"] = True
    employee_access[emp_id]["source"] = "face"
    state_module.current_employee_id = emp_id

    return f"✅ Face registration completed for Employee ID {emp_id}. You're all set."


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
        # If already authenticated in this session, do not run retry
        try:
            from Modules.state import current_employee_id
            emp_id_now = current_employee_id
        except Exception:
            emp_id_now = None

        if emp_id_now:
            empid_norm = str(emp_id_now).strip().upper()
            if employee_access.get(empid_norm, {}).get("granted", False):
                # Already authenticated; avoid duplicate prompts
                return "You're already authenticated. How can I assist you today?"

        # Use default embeddings path if not provided
        if embeddings_path is None:
            embeddings_path = os.getenv("VR_FACE_EMBEDDINGS", "face_embeddings.pkl")
        
        # Load employee database
        employee_csv = os.getenv("VR_EMPLOYEE_CSV", "data/employee_details.csv")
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
                            # Mark access granted via face recognition (normalized)
                            empid_norm_key = str(emp_id).strip().upper()
                            employee_access[empid_norm_key]["granted"] = True
                            employee_access[empid_norm_key]["source"] = "face"
                            state_module.current_employee_id = empid_norm_key
                            
                            return f"SUCCESS: Hello {name}! Welcome back! How can I assist you today? (Employee verified via face recognition)"
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
    logger.info("start_face_greeting invoked (wait_for_wake=%s, timeout_s=%s)", wait_for_wake, timeout_s)
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
        logger.info("Face recognition completed; message to speak: %s", msg)
        
        # Ensure we always return a message
        if msg is None:
            msg = "Your face is not in our database. Would you like to register your face now?"
            print(f"DEBUG: msg was None, using fallback: {msg}")
            logger.warning("_first_decision returned None; using fallback message")
        
        # Mark face recognition as completed
        state_module.face_recognition_completed = True
        
        # Log the final message being returned
        print(f"DEBUG: Final message being returned to agent: {msg}")
        logger.info("Returning message to LLM: %s", msg)
        
        # Return the result - Clara will speak this
        return msg
        
    except Exception as e:
        print(f"ERROR in start_face_greeting: {e}")
        import traceback
        traceback.print_exc()
        # Mark face recognition as completed even on error
        state_module.face_recognition_completed = True
        # Return a fallback message
        return "Your face is not in our database. Would you like to register your face now?"


