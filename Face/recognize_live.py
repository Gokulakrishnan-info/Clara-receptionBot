import sys
import os

# Add the src directory of the anti-spoofing repo to sys.path (disabled)
# anti_spoof_src = r"C:\Users\Gokulakrishnan\Desktop\Face\Silent_Face_Anti_Spoofing_master\src"
# sys.path.append(anti_spoof_src)

import cv2
import pickle
import numpy as np
import insightface

# from Silent_Face_Anti_Spoofing_master.src.anti_spoof_predict import AntiSpoofPredict
# from Silent_Face_Anti_Spoofing_master.src.generate_patches import CropImage
# from Silent_Face_Anti_Spoofing_master.src.utility import parse_model_name

EMBEDDINGS_FILE = r"C:\Users\Gokulakrishnan\Desktop\Face\Faces\face_embeddings.pkl"
# ANTI_SPOOF_MODEL_PATH = r"C:\Users\Gokulakrishnan\Desktop\Face\Silent_Face_Anti_Spoofing_master\resources\anti_spoof_models\2.7_80x80_MiniFASNetV2.pth"

FRAME_SKIP = 1
# ANTI_SPOOF_SKIP = 2
THRESHOLD =  0.65 #0.5  # Recognition threshold

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_embeddings(path):
    with open(path, "rb") as f:
        embeddings_dict = pickle.load(f)
    
    # Normalize all embeddings
    for k, v in embeddings_dict.items():
        v = np.array(v).flatten() # Ensure it's a 2D array
        embeddings_dict[k] = v / np.linalg.norm(v)
    return embeddings_dict

def recognize_face(face_embedding, embeddings_dict, threshold=THRESHOLD):
    best_score = -1
    best_name = "Unknown"
    for name, db_emb in embeddings_dict.items():
        # db_emb = np.array(db_emb).flatten()
        score = cosine_similarity(face_embedding, db_emb)

        if score > best_score:
            best_score = score
            best_name = name

    if best_score >= threshold:
        return best_name, best_score
    else:
        return "Unknown", best_score

def main():
    embeddings_dict = load_embeddings(EMBEDDINGS_FILE)
    model = insightface.app.FaceAnalysis(name="buffalo_l",providers=['CPUExecutionProvider'])
    model.prepare(ctx_id=0, det_size=(640, 640))

    # Anti-spoofing setup (disabled)
    # anti_spoof = AntiSpoofPredict(0)
    # cropper = CropImage()
    # h_input, w_input, _, scale = parse_model_name(os.path.basename(ANTI_SPOOF_MODEL_PATH))

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("Press 'q' to quit.")

    frame_count = 0
    # last_is_real = True  # Assume real at start

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        # Skip some frames to reduce processing
        if frame_count % FRAME_SKIP != 0:  # process every Nth frame
            cv2.imshow("Face Recognition", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        faces = model.get(frame)
        for face in faces:
            bbox = face.bbox.astype(int)
            # Anti-spoofing (disabled)
            # param = {
            #     "org_img": frame,
            #     "bbox": bbox,
            #     "scale": scale,
            #     "out_w": w_input,
            #     "out_h": h_input,
            #     "crop": True if scale is not None else False,
            # }
            # if frame_count % ANTI_SPOOF_SKIP == 0:
            #     img_cropped = cropper.crop(**param)
            #     prediction = anti_spoof.predict(img_cropped, ANTI_SPOOF_MODEL_PATH)
            #     real_prob = float(prediction[0][1])
            #     print(f"Anti-Spoofing Real Probability: {real_prob:.3f}")
            #     last_is_real = real_prob > 0.3
            
             

            # if not last_is_real:  
            #     name = "Spoof Detected"
            #     color = (0, 0, 255)
            #     print("Spoof detected!")
            # else:
            #     embedding = face.embedding.astype(np.float32).flatten()
            #     embedding = embedding / np.linalg.norm(embedding) # Normalize
            #     name, score = recognize_face(embedding, embeddings_dict)
            #     color = (0, 255, 0) if name != "Unknown" else (0, 255, 255)
            #     print(f"Detected: {name} (score={score:.3f})")

            embedding = face.embedding.astype(np.float32).flatten()
            embedding = embedding / np.linalg.norm(embedding) # Normalize
            name, score = recognize_face(embedding, embeddings_dict)
            color = (0, 255, 0) if name != "Unknown" else (0, 255, 255)
            print(f"Detected: {name} (score={score:.3f})")

            # Draw bounding box and name
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            cv2.putText(frame, f"{name}", (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break 

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()