from collections import defaultdict

# Shared in-memory sessions/state
otp_sessions = defaultdict(dict)

# Auth/access flags keyed by employee id
employee_access = defaultdict(lambda: {"granted": False, "source": None})

# Voice control state
is_awake = True

# Face recognition state
face_recognition_completed = False

# Current authenticated employee
current_employee_id = None

# Current user's declared role for gating flows: 'employee' | 'candidate' | 'visitor' | None
selected_role = None


