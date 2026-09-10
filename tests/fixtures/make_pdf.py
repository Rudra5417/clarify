from fpdf import FPDF


def pdf_with_n_pages(n: int) -> bytes:
    pdf = FPDF()
    for i in range(1, n + 1):
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(40, 10, f"page {i}")
    return bytes(pdf.output())


def pdf_with_text(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, text)
    return bytes(pdf.output())


def pdf_blank() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())
