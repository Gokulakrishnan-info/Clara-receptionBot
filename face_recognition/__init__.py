"""
Face Recognition Module

This module contains all face recognition functionality including:
- Face detection and recognition
- Face enrollment
- Face integration with the virtual receptionist
"""

from .recognize_wrapper import Recognizer, draw_detections
from .face_integration import (
    start_face_greeting,
    retry_face_recognition,
    reset_face_recognition_state,
    new_user_detected,
    register_employee_face,
    request_employee_face_registration,
    complete_employee_face_registration
)

__all__ = [
    "Recognizer",
    "draw_detections",
    "start_face_greeting",
    "retry_face_recognition",
    "reset_face_recognition_state",
    "new_user_detected",
    "register_employee_face",
    "request_employee_face_registration",
    "complete_employee_face_registration"
]
