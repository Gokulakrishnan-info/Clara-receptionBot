"""
Virtual Receptionist Tools - Legacy Compatibility Layer

This file provides backward compatibility by importing and re-exporting
all tools from the modular structure in the Modules/ folder.

All actual tool implementations are now in:
- Modules/company_info.py
- Modules/get_employee_details.py
- Modules/get_my_employee_info.py
- Modules/get_candidate_details.py
- Modules/log_and_notify_visitor.py
- Modules/listen_for_commands.py
- Modules/search_web.py
- Modules/get_weather.py
- Modules/send_email.py
- face_integration.py

This file is kept for backward compatibility but should not be modified.
All new tools should be added to the appropriate module in Modules/.
"""

# Import all tools from the modular structure
from Modules.tools_registry import (
    company_info,
    get_employee_details,
    is_employee_authenticated,
    get_my_employee_info,
    get_employee_by_name,
    get_candidate_details,
    log_and_notify_visitor,
    listen_for_commands,
    search_web,
    get_weather,
    send_email,
)

# Import face recognition tools
from face_integration import start_face_greeting, retry_face_recognition

# Re-export all tools for backward compatibility
__all__ = [
    "company_info",
    "get_employee_details", 
    "is_employee_authenticated",
    "get_my_employee_info",
    "get_employee_by_name",
    "get_candidate_details",
    "log_and_notify_visitor",
    "listen_for_commands",
    "search_web",
    "get_weather",
    "send_email",
    "start_face_greeting",
    "retry_face_recognition",
]

# Legacy compatibility - these are now handled by Modules/state.py
from Modules.state import otp_sessions, employee_access, is_awake
from Modules.config import WAKE_WORD as wake_word, SLEEP_PHRASE as sleep_phrase

# Note: All tool implementations have been moved to their respective modules.
# This file now serves as a compatibility layer only.