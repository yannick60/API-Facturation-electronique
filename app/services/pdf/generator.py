from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.models.invoice import Invoice, InvoiceLine
from app.models.company import Company
from app.models.client import Client
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)

class InvoicePDFGenerator :

    def __init__(self):
        self.template = env.get_template("invoice.html")
    
    def invoice_pdf_service(self,company:Company,client:Client,invoice:Invoice, invoice_lines:InvoiceLine) :
        html = self.template.render(
            company=company,
            client=client,
            invoice=invoice,
            invoice_lines=invoice_lines,
        )
        pdf = HTML(string=html).write_pdf()

        return pdf