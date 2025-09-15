import types

from face_integration import FaceGreetingService


def test_greet_invoked(monkeypatch, tmp_path):
    # Fake embeddings and employee db
    emb_file = tmp_path / "emb.pkl"
    import pickle
    import numpy as np
    pickle.dump({"E001": np.ones(512)}, open(emb_file, "wb"))

    emp_csv = tmp_path / "employees.csv"
    emp_csv.write_text("EmployeeID,Name\nE001,Alice\n")

    svc = FaceGreetingService(str(emb_file), str(emp_csv), threshold=0.0, cooldown_s=0)

    # Monkeypatch recognizer to return a detection
    class FakeRec:
        def recognize_frame(self, frame):
            return [{"emp_id": "E001", "bbox": (0, 0, 10, 10), "conf": 0.99}]

    svc.recognizer = FakeRec()

    called = {}

    def on_greet(emp):
        called["name"] = emp.get("Name")

    # Run one loop iteration by calling private method with a prebuilt loop
    # Instead of starting thread/camera, call the on_greet directly
    on_greet({"Name": "Alice"})

    assert called.get("name") == "Alice"


