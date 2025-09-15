import re
import random
from datetime import datetime

import pandas as pd
from livekit.agents import function_tool, RunContext

from . import config
from .state import otp_sessions, employee_access
from .send_email import send_email_smtp


def is_employee_authenticated(employee_id: str) -> bool:
    """Check if employee is authenticated via face recognition or OTP."""
    empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()
    return employee_access.get(empid_norm, {}).get("granted", False)


@function_tool()
async def get_employee_details(context: RunContext, name: str, employee_id: str, otp: str = None) -> str:
    """
    Employee verification via OTP emailed to employee's address.
    If employee was authenticated via face recognition, skip OTP and grant access directly.
    After OTP success, optionally greet if manager visit is scheduled today.
    """
    try:
        empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()
        
        # Check if employee was authenticated via face recognition FIRST
        if employee_access.get(empid_norm, {}).get("granted") and employee_access[empid_norm]["source"] == "face":
            # Skip all validation for face-recognized employees
            df = pd.read_csv(config.EMPLOYEE_CSV)
            df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()
            
            id_match = df[df["EmployeeID_norm"] == empid_norm]
            if id_match.empty:
                return "❌ Employee ID not found. Please recheck it."
            
            record = id_match.iloc[0]
            emp_name = record["Name"]
            # Skip OTP verification for face-recognized employees
            try:
                df_mgr = pd.read_csv(config.MANAGER_VISIT_CSV, dtype=str).fillna("")
                df_mgr["Visit Date"] = pd.to_datetime(df_mgr["Visit Date"]).dt.strftime("%Y-%m-%d")
                today = datetime.now().strftime("%Y-%m-%d")
                mgr_match = df_mgr[
                    (df_mgr["EmployeeID"].astype(str).str.strip().str.upper() == empid_norm)
                    & (df_mgr["Visit Date"] == today)
                ]
                if not mgr_match.empty:
                    office = mgr_match.iloc[0]["Office"]
                    return (
                        f"✅ Welcome back, {emp_name}! 🎉\n"
                        "Hope you had a smooth and comfortable journey. "
                        f"It was wonderful having you at our {office} office! "
                        "We truly hope your visit was both memorable and meaningful. "
                        f"Thanks so much for taking the time to be with us—it really meant a lot to the whole {office} team. "
                        "You have full access to all tools."
                    )
            except FileNotFoundError:
                pass
            
            return f"✅ Welcome back, {emp_name}! You have full access to all tools."
        
        # Regular validation for non-face-recognized employees
        df = pd.read_csv(config.EMPLOYEE_CSV)
        df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
        df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()

        name_norm = re.sub(r"\s+", " ", name).strip().lower()

        id_match = df[df["EmployeeID_norm"] == empid_norm]
        if id_match.empty:
            return "❌ Employee ID not found. Please recheck it."

        match = id_match[id_match["Name_norm"] == name_norm]
        if match.empty:
            return "❌ Name and Employee ID don't match. Please try again."

        record = match.iloc[0]
        email = str(record["Email"]).strip()
        emp_name = record["Name"]

        if email not in otp_sessions:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}

        if otp is None:
            generated_otp = str(random.randint(100000, 999999))
            otp_sessions[email]["otp"] = generated_otp
            otp_sessions[email]["verified"] = False
            otp_sessions[email]["attempts"] = 0
            otp_sessions[email]["name"] = emp_name
            otp_sessions[email]["employee_id"] = record["EmployeeID"]

            subject = "Your One-Time Password (OTP)"
            body = f"Hello {emp_name}, your OTP is: {generated_otp}"
            try:
                send_email_smtp([email], subject, body)
            except Exception as e:
                return f"❌ Error sending OTP: {str(e)}"

            return f"✅ Hi {emp_name}, I sent an OTP to your email ({email}). 👉 Please tell me the OTP now."

        saved_otp = otp_sessions[email].get("otp")
        attempts = otp_sessions[email].get("attempts", 0)

        if attempts >= 3:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}
            return "❌ Too many failed attempts. Restart verification from the beginning."

        if saved_otp and otp.strip() == saved_otp:
            otp_sessions[email]["verified"] = True
            # Mark employee as authenticated via OTP
            employee_access[empid_norm]["granted"] = True
            employee_access[empid_norm]["source"] = "otp"

            try:
                df_mgr = pd.read_csv(config.MANAGER_VISIT_CSV, dtype=str).fillna("")
                df_mgr["Visit Date"] = pd.to_datetime(df_mgr["Visit Date"]).dt.strftime("%Y-%m-%d")
                today = datetime.now().strftime("%Y-%m-%d")
                mgr_match = df_mgr[
                    (df_mgr["EmployeeID"].astype(str).str.strip().str.upper() == empid_norm)
                    & (df_mgr["Visit Date"] == today)
                ]
                if not mgr_match.empty:
                    office = mgr_match.iloc[0]["Office"]
                    return (
                        f"✅ OTP verified. Welcome {emp_name}! 🎉\n"
                        "Hope you had a smooth and comfortable journey"
                        f"It was wonderful having you at our {office} office!"
                        "We truly hope your visit was both memorable and meaningful."
                        f"Thanks so much for taking the time to be with us—it really meant a lot to the whole {office} team."
                    )
            except FileNotFoundError:
                pass

            return f"✅ OTP verified. Welcome {emp_name}! You now have full access to all tools."
        else:
            otp_sessions[email]["attempts"] = attempts + 1
            return f"❌ OTP incorrect. Attempts left: {3 - (attempts + 1)}."

    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying employee: {str(e)}"


