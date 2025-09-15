import os
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from livekit.agents import function_tool, RunContext

from . import config

# Simple session memory
otp_sessions = {}


@function_tool()
async def get_candidate_details(context: RunContext, candidate_name: str, interview_code: str) -> str:
    try:
        df_candidates = pd.read_csv(config.CANDIDATE_CSV, dtype=str).fillna("")
        df_candidates["InterviewCode_norm"] = (
            df_candidates["Interview Code"].astype(str).str.encode("ascii", "ignore").str.decode("ascii").str.strip().str.replace(r"[^0-9A-Za-z]", "", regex=True).str.upper()
        )
        df_candidates["Candidate_norm"] = (
            df_candidates["Candidate Name"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True).str.lower()
        )

        code_norm = interview_code.encode("ascii", "ignore").decode("ascii").strip().upper()
        cand_name_norm = candidate_name.encode("ascii", "ignore").decode("ascii").strip().lower()

        record_match = df_candidates[df_candidates["InterviewCode_norm"] == code_norm]
        if record_match.empty:
            return f"❌ Interview code '{interview_code}' not found in today’s list."

        record = record_match.iloc[0]
        if cand_name_norm != record["Candidate_norm"]:
            return (
                f"❌ The name '{candidate_name}' does not match our records "
                f"for interview code {interview_code}. Please recheck."
            )

        sess = otp_sessions.setdefault(code_norm, {"attempts": 0, "verified": False})
        if sess["attempts"] >= 3:
            otp_sessions.pop(code_norm, None)
            return "❌ Too many failed attempts. Please restart candidate verification."

        interviewer_name = str(record["Interviewer"]).strip()
        cand_role = record["Interview Role"]
        cand_time = record["Interview Time"]

        df_employees = pd.read_csv(config.EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = df_employees["Name"].astype(str).str.strip().str.lower()
        interviewer = df_employees[df_employees["Name_norm"] == interviewer_name.strip().lower()]
        if interviewer.empty:
            return f"❌ Interviewer '{interviewer_name}' not found in employee records."

        interviewer_email = interviewer.iloc[0]["Email"]

        gmail_user = config.GMAIL_USER
        gmail_password = config.GMAIL_APP_PASSWORD
        if not gmail_user or not gmail_password:
            return "❌ Email sending failed: Gmail credentials not configured."

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = interviewer_email
        msg["Subject"] = f"Candidate {record['Candidate Name']} has arrived for interview"
        body = (
            f"Hi {interviewer_name},\n\n"
            f"Candidate {record['Candidate Name']} has arrived for the {cand_role} interview.\n\n"
            f"Interview Time: {cand_time}\n"
            f"Interview Code: {record['Interview Code']}\n\n"
            "Please let me know if you're ready to meet them."
        )
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [interviewer_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Error sending email to interviewer: {str(e)}"

        sess["verified"] = True
        return (
            f"✅ Hello {record['Candidate Name']}, your interview for {cand_role} is scheduled at {cand_time}. "
            f"Please wait for a few moments, {interviewer_name} will meet you shortly."
        )

    except FileNotFoundError:
        return "❌ Candidate or employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying candidate: {str(e)}"


