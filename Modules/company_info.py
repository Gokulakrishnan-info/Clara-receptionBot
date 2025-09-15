import os
from PyPDF2 import PdfReader
from livekit.agents import function_tool, RunContext

from . import config


@function_tool()
async def company_info(context: RunContext, query: str = "general") -> str:
    """
    Fetch company information from company_info.pdf.
    If query == "general", returns the first ~600 chars.
    Otherwise searches for the keyword within the text.
    """
    try:
        pdf_path = config.COMPANY_INFO_PDF
        if not os.path.exists(pdf_path):
            return "Company information file is missing."

        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

        if not text.strip():
            return "Company information could not be extracted."

        if query.lower() == "general":
            return text[:600] + "..."

        q = query.lower()
        matches = [line for line in text.split("\n") if q in line.lower()]
        if matches:
            return " | ".join(matches[:5])
        else:
            return f"No specific details found for '{query}'."

    except Exception as e:
        return f"Error reading company information: {str(e)}"


