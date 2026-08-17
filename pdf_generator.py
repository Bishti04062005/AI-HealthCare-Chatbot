"""
pdf_generator.py
Builds a downloadable PDF transcript of the chat conversation, using fpdf2.
"""

from datetime import datetime

try:
    from fpdf import FPDF  # type: ignore
except ImportError:  # pragma: no cover - give a helpful import error
    raise ImportError(
        "fpdf (fpdf2) is required to generate PDFs. Install with: pip install fpdf2"
    ) from None

DISCLAIMER = (
    "This document is a record of an AI-generated conversation for general informational "
    "purposes only. It is not medical advice, diagnosis, or treatment, and should not be "
    "used as a substitute for consultation with a qualified healthcare professional."
)


class ChatPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 90, 130)
        self.cell(0, 10, "AI Healthcare Chatbot - Conversation Transcript", ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(110, 110, 110)
        self.cell(0, 6, datetime.now().strftime("Generated on %B %d, %Y at %I:%M %p"), ln=True, align="C")
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _write_wrapped(pdf: ChatPDF, label: str, text: str, label_color, fill_color):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*label_color)
    pdf.cell(0, 7, label, ln=True)

    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(20, 20, 20)
    pdf.set_fill_color(*fill_color)
    # multi_cell handles wrapping; fill gives each bubble a light background band
    pdf.multi_cell(0, 6, text, fill=True)
    pdf.ln(3)


def generate_chat_pdf(messages: list) -> bytes:
    """
    messages: list of dicts like {"role": "user"|"assistant", "content": str}
    Returns: PDF file content as bytes, ready for st.download_button.
    """
    pdf = ChatPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Disclaimer box
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 60, 20)
    pdf.set_fill_color(255, 244, 224)
    pdf.multi_cell(0, 5.5, DISCLAIMER, fill=True)
    pdf.ln(4)

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Encode to latin-1-safe text since core fpdf fonts don't support full Unicode.
        safe_content = content.encode("latin-1", "replace").decode("latin-1")

        if role == "user":
            _write_wrapped(pdf, "You asked:", safe_content, (20, 90, 150), (232, 242, 250))
        else:
            _write_wrapped(pdf, "HealthGuide AI:", safe_content, (30, 130, 90), (232, 250, 240))

    return bytes(pdf.output(dest="S"))