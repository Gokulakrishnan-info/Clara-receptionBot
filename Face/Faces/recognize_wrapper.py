# Faces/recognize_wrapper.py
"""
Thin wrapper around Faces/recognize_live.py to provide:
recognize_frame(frame) -> List[{'emp_id': str|None, 'bbox':(x,y,w,h), 'conf': float}]
Also optionally consults an anti-spoof module if present.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np

# import the heavy module (it's expected to already initialize app & embeddings on import)
try:
    from Faces import recognize_live as rl
except Exception:
    # if run as top-level without package imports, fallback to relative import
    import recognize_live as rl

# Try to import an anti-spoof module if it exists - flexible API:
# - If it has `is_live(frame, bbox)` -> call that
# - If it has `predict(frame, bbox)` -> call that (truthy == live)
anti_spoof = None
try:
    import Faces.anti_spoof as anti
    anti_spoof = anti
except Exception:
    try:
        import anti_spoof as anti
        anti_spoof = anti
    except Exception:
        anti_spoof = None


def _bbox_from_face(face) -> Tuple[int, int, int, int]:
    # insightface face.bbox is [x1, y1, x2, y2] or similar. Return x, y, w, h ints
    bbox = getattr(face, "bbox", None)
    if bbox is None:
        return (0, 0, 0, 0)
    # ensure numpy array
    b = np.asarray(bbox).astype(int).flatten()
    x1, y1, x2, y2 = int(b[0]), int(b[1]), int(b[2]), int(b[3])
    w = max(0, x2 - x1)
    h = max(0, y2 - y1)
    return (x1, y1, w, h)


def recognize_frame(frame) -> List[Dict]:
    """
    Run face detection/recognition on a single BGR frame.

    Returns list of detections:
      {"emp_id": str|None, "bbox": (x,y,w,h), "conf": float}
    where conf is cosine similarity score (0..1 typical).
    If no faces found -> returns [].
    """
    # use insightface app directly from recognize_live
    faces = rl.app.get(frame)
    results = []

    if not faces:
        return []

    for face in faces:
        # compute embedding matching
        embedding = getattr(face, "embedding", None)
        if embedding is None:
            # skip if no embedding
            continue

        best_match = None
        best_score = 0.0
        for emp_id, emp_emb in rl.employee_db.items():
            sim = rl.cosine_similarity(embedding, emp_emb)
            if sim > best_score:
                best_score = float(sim)
                best_match = emp_id

        bbox = _bbox_from_face(face)
        # If anti-spoof exists, call it and attach flag
        is_live = True
        if anti_spoof:
            try:
                # flexible: prefer is_live(frame, bbox) signature
                if hasattr(anti_spoof, "is_live"):
                    is_live = bool(anti_spoof.is_live(frame, bbox))
                elif hasattr(anti_spoof, "predict"):
                    is_live = bool(anti_spoof.predict(frame, bbox))
                else:
                    is_live = True
            except Exception:
                # on errors, default to True (don't block)
                is_live = True

        results.append(
            {
                "emp_id": best_match if best_score >= rl.SIMILARITY_THRESHOLD else None,
                "bbox": bbox,
                "conf": float(best_score),
                "is_live": bool(is_live),
            }
        )

    return results


# optional helper to return only best detection
def recognize_best(frame):
    dets = recognize_frame(frame)
    if not dets:
        return None
    # return detection with maximum conf
    return max(dets, key=lambda d: d["conf"])
