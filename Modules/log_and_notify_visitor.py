import pandas as pd
from datetime import datetime
from livekit.agents import function_tool, RunContext

from . import config
from .send_email import send_email_smtp


@function_tool()
async def log_and_notify_visitor(context: RunContext, visitor_name: str, phone: str, purpose: str, meeting_employee: str) -> str:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "Visitor Name": visitor_name,
            "Phone": phone,
            "Purpose": purpose,
            "Meeting Employee": meeting_employee,
            "Timestamp": timestamp,
        }

        try:
            df = pd.read_csv(config.VISITOR_LOG)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Visitor Name", "Phone", "Purpose", "Meeting Employee", "Timestamp"])

        df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        df.to_csv(config.VISITOR_LOG, index=False)

        df_employees = pd.read_csv(config.EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = df_employees["Name"].str.strip().str.lower()
        emp_match = df_employees[df_employees["Name_norm"] == meeting_employee.strip().lower()]
        if emp_match.empty:
            return f"❌ Employee '{meeting_employee}' not found in records."

        emp_email = emp_match.iloc[0]["Email"]

        subject = f"Visitor {visitor_name} is waiting for you at reception"
        body = (
            f"Hi {meeting_employee},\n\n"
            f"A visitor has arrived to meet you.\n\n"
            f"Name: {visitor_name}\n"
            f"Phone: {phone}\n"
            f"Purpose: {purpose}\n"
            f"Arrived at: {timestamp}\n\n"
            "Please proceed to reception."
        )

        try:
            send_email_smtp([emp_email], subject, body)
        except Exception as e:
            return f"❌ Error sending visitor email: {str(e)}"

        return f"✅ Visitor {visitor_name} logged and {meeting_employee} has been notified by email."

    except Exception as e:
        return f"❌ Error in visitor flow: {str(e)}"


