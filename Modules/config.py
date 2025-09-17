import os
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

# Base directory for relative paths (defaults to project root when run here)
BASE_DIR = os.getenv("VR_BASE_DIR", os.getcwd())

# Data file paths (env overrideable)
EMPLOYEE_CSV = os.getenv(
    "VR_EMPLOYEE_CSV",
    os.path.join(BASE_DIR, "data", "employee_details.csv"),
)
CANDIDATE_CSV = os.getenv(
    "VR_CANDIDATE_CSV",
    os.path.join(BASE_DIR, "data", "candidate_interview.csv"),
)
COMPANY_INFO_PDF = os.getenv(
    "VR_COMPANY_INFO_PDF",
    os.path.join(BASE_DIR, "data", "company_info.pdf"),
)
VISITOR_LOG = os.getenv(
    "VR_VISITOR_LOG",
    os.path.join(BASE_DIR, "data", "visitor_log.csv"),
)
MANAGER_VISIT_CSV = os.getenv(
    "VR_MANAGER_VISIT_CSV",
    os.path.join(BASE_DIR, "data", "manager_visit.csv"),
)

# Wake/sleep defaults (env overrideable)
WAKE_WORD = os.getenv("VR_WAKE_WORD", "Clara").lower()
SLEEP_PHRASE = os.getenv("VR_SLEEP_PHRASE", "don't talk anything").lower()

# Gmail credentials (read by email helper)
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


