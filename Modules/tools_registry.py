from .company_info import company_info
from .get_employee_details import get_employee_details, is_employee_authenticated
from .get_my_employee_info import get_my_employee_info, get_employee_by_name, get_employee_field, who_am_i
from .get_candidate_details import get_candidate_details
from .log_and_notify_visitor import log_and_notify_visitor
from .listen_for_commands import listen_for_commands
from .search_web import search_web
from .get_weather import get_weather
from .send_email import send_email
from livekit.agents import function_tool, RunContext
from . import state as s

@function_tool()
async def set_role(context: RunContext, role: str) -> str:
    """Set current user's role to 'employee' | 'candidate' | 'visitor'."""
    role_l = (role or "").strip().lower()
    if role_l not in {"employee", "candidate", "visitor"}:
        return "❌ Please say employee, candidate, or visitor."
    s.selected_role = role_l
    return f"Role set to {role_l}."

__all__ = [
    "company_info",
    "get_employee_details",
    "is_employee_authenticated",
    "get_my_employee_info",
    "get_employee_by_name",
    "get_employee_field",
    "who_am_i",
    "get_candidate_details",
    "log_and_notify_visitor",
    "listen_for_commands",
    "search_web",
    "get_weather",
    "send_email",
    "set_role",
]


