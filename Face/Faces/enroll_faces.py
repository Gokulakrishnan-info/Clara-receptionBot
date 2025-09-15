import os
import pickle
import cv2
import insightface
import numpy as np
from collections import defaultdict


# Path to your face database folder
FACE_DB_DIR = r"C:\Users\Gokulakrishnan\Documents\virtual-receptionist-main\Employee\EMP_Photos"
# Output pickle file
EMBEDDINGS_FILE = r"C:\Users\Gokulakrishnan\Documents\virtual-receptionist-main\face_embeddings.pkl"

def get_employee_id(filename):
    # Extract employee ID or name from filename (without extension)
    return os.path.splitext(filename)[0]

def main():
    # Load InsightFace model
    model = insightface.app.FaceAnalysis(name="buffalo_l",providers=['CPUExecutionProvider'])
    model.prepare(ctx_id=0, det_size=(640, 640))

    embeddings_dict = defaultdict(list) # To hold embeddings

    for fname in os.listdir(FACE_DB_DIR):
        fpath = os.path.join(FACE_DB_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        img = cv2.imread(fpath)
        if img is None:
            print(f"Could not read {fname}, skipping.")
            continue

        faces = model.get(img)
        if not faces:
            print(f"No face found in {fname}, skipping.")
            continue

        # Use the first detected face
        embedding = faces[0].embedding.astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding) # Normalize

        emp_id = get_employee_id(fname)
        embeddings_dict[emp_id].append(embedding)
        print(f"Captured embedding for {emp_id} from {fname}")

    # Save all embeddings to a pickle file
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(embeddings_dict, f)
    print(f"✅ Enrollment complete. Saved to {EMBEDDINGS_FILE}")

if __name__ == "__main__":
    main()