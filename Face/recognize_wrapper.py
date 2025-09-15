import os
import pickle
from typing import List, Dict, Tuple

import cv2
import numpy as np
import insightface


class Recognizer:
    def __init__(self, embeddings_path: str, threshold: float = 0.65):
        self.embeddings_path = embeddings_path
        self.threshold = float(os.getenv("VR_FACE_THRESHOLD", threshold))
        self._embeddings = self._load_embeddings(embeddings_path)
        self._face = insightface.app.FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
        self._face.prepare(ctx_id=0, det_size=(640, 640))

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _load_embeddings(self, path: str) -> Dict[str, np.ndarray]:
        with open(path, "rb") as f:
            data = pickle.load(f)
        normalized = {}
        for key, vec in data.items():
            arr = np.array(vec).flatten().astype(np.float32)
            norm = np.linalg.norm(arr)
            if norm == 0:
                continue
            normalized[key] = arr / norm
        return normalized

    def recognize_frame(self, frame) -> List[Dict]:
        results: List[Dict] = []
        faces = self._face.get(frame)
        for face in faces:
            bbox = face.bbox.astype(int)
            emb = face.embedding.astype(np.float32).flatten()
            norm = np.linalg.norm(emb)
            if norm == 0:
                continue
            emb = emb / norm

            best_id = "Unknown"
            best_score = -1.0
            for label, db_emb in self._embeddings.items():
                score = self._cosine_similarity(emb, db_emb)
                if score > best_score:
                    best_score = score
                    best_id = label

            emp_id = best_id if best_score >= self.threshold else "Unknown"
            results.append({
                "emp_id": emp_id,
                "bbox": (int(bbox[0]), int(bbox[1]), int(bbox[2]-bbox[0]), int(bbox[3]-bbox[1])),
                "conf": float(best_score),
            })
        return results


def draw_detections(frame, detections: List[Dict]):
    for det in detections:
        x, y, w, h = det["bbox"]
        label = f"{det['emp_id']}" if det["emp_id"] != "Unknown" else "Unknown"
        color = (0, 255, 0) if det["emp_id"] != "Unknown" else (0, 255, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return frame


