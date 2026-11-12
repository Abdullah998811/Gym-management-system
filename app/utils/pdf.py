import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def p_text(text):
    """Safely XML-escape text before inserting into ReportLab Paragraph."""
    if text is None:
        return ""
    return xml_escape(str(text))

def generate_member_card_pdf(member):
    """Generate a printable Gym Membership Card PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(3.5 * inch, 2.25 * inch),  # ID Card size (standard CR80 approx)
        rightMargin=12,
        leftMargin=12,
        topMargin=12,
        bottomMargin=12
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#0d6efd'),
        alignment=1
    )
    sub_style = ParagraphStyle(
        'CardSub',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#6c757d')
    )
    body_style = ParagraphStyle(
        'CardBody',
        parent=styles['Normal'],
        fontSize=7,
        leading=9
    )

    elements = [
        Paragraph("<b>TITAN FITNESS & GYM</b>", title_style),
        Paragraph("OFFICIAL MEMBERSHIP CARD", sub_style),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0d6efd'), spaceAfter=6),
    ]

    card_data = [
        [Paragraph("<b>Name:</b>", body_style), Paragraph(p_text(member.full_name), body_style)],
        [Paragraph("<b>Member ID:</b>", body_style), Paragraph(p_text(member.membership_number), body_style)],
        [Paragraph("<b>CNIC:</b>", body_style), Paragraph(p_text(member.cnic), body_style)],
        [Paragraph("<b>Phone:</b>", body_style), Paragraph(p_text(member.phone), body_style)],
        [Paragraph("<b>Joined:</b>", body_style), Paragraph(p_text(member.join_date), body_style)],
        [Paragraph("<b>Branch:</b>", body_style), Paragraph(p_text(member.branch.name if member.branch else "Main Branch"), body_style)]
    ]

    table = Table(card_data, colWidths=[65, 160])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()

def generate_invoice_pdf(invoice):
    """Generate an official Invoice / Receipt PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'InvTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0d6efd')
    )
    meta_style = ParagraphStyle(
        'InvMeta',
        parent=styles['Normal'],
        fontSize=9,
        leading=12
    )

    elements = [
        Paragraph("<b>TITAN FITNESS & GYM SYSTEM</b>", title_style),
        Paragraph("INVOICE & PAYMENT RECEIPT", styles['Heading3']),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=12),
    ]

    # Meta info table
    header_data = [
        [
            Paragraph(f"<b>Invoice #:</b> {p_text(invoice.invoice_number)}<br/>"
                      f"<b>Issue Date:</b> {p_text(invoice.issue_date)}<br/>"
                      f"<b>Due Date:</b> {p_text(invoice.due_date)}<br/>"
                      f"<b>Status:</b> <b>{p_text(invoice.payment_status.upper())}</b>", meta_style),
            Paragraph(f"<b>Billed To:</b><br/>"
                      f"<b>Member:</b> {p_text(invoice.member.full_name)}<br/>"
                      f"<b>Member ID:</b> {p_text(invoice.member.membership_number)}<br/>"
                      f"<b>Phone:</b> {p_text(invoice.member.phone)}<br/>"
                      f"<b>Email:</b> {p_text(invoice.member.email)}", meta_style)
        ]
    ]
    meta_table = Table(header_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 16))

    # Items table
    items_data = [
        [Paragraph("<b>Item / Description</b>", meta_style),
         Paragraph("<b>Qty</b>", meta_style),
         Paragraph("<b>Unit Price (PKR)</b>", meta_style),
         Paragraph("<b>Total (PKR)</b>", meta_style)]
    ]

    for item in invoice.items:
        items_data.append([
            Paragraph(p_text(item.description), meta_style),
            Paragraph(str(item.quantity), meta_style),
            Paragraph(f"{float(item.unit_price):,.2f}", meta_style),
            Paragraph(f"{float(item.total_price):,.2f}", meta_style),
        ])

    if not invoice.items:
        items_data.append([
            Paragraph("Gym Membership Fee", meta_style),
            Paragraph("1", meta_style),
            Paragraph(f"{float(invoice.subtotal):,.2f}", meta_style),
            Paragraph(f"{float(invoice.subtotal):,.2f}", meta_style),
        ])

    num_item_rows = len(invoice.items) if invoice.items else 1

    # Summary rows
    items_data.append(["", "", Paragraph("<b>Subtotal:</b>", meta_style), Paragraph(f"PKR {float(invoice.subtotal):,.2f}", meta_style)])
    if invoice.discount_amount > 0:
        items_data.append(["", "", Paragraph("<b>Discount:</b>", meta_style), Paragraph(f"- PKR {float(invoice.discount_amount):,.2f}", meta_style)])
    if invoice.tax_amount > 0:
        items_data.append(["", "", Paragraph("<b>Tax:</b>", meta_style), Paragraph(f"PKR {float(invoice.tax_amount):,.2f}", meta_style)])
    items_data.append(["", "", Paragraph("<b>Total Amount:</b>", meta_style), Paragraph(f"<b>PKR {float(invoice.total_amount):,.2f}</b>", meta_style)])
    items_data.append(["", "", Paragraph("<b>Amount Paid:</b>", meta_style), Paragraph(f"PKR {float(invoice.paid_amount):,.2f}", meta_style)])
    items_data.append(["", "", Paragraph("<b>Balance Due:</b>", meta_style), Paragraph(f"<b>PKR {float(invoice.balance_due):,.2f}</b>", meta_style)])

    total_rows = len(items_data)

    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#0d6efd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, num_item_rows), 0.5, colors.HexColor('#dee2e6')),
        ('GRID', (2, num_item_rows + 1), (-1, total_rows - 1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]

    table = Table(items_data, colWidths=[240, 50, 120, 130])
    table.setStyle(TableStyle(table_style))
    elements.append(table)
    elements.append(Spacer(1, 24))

    # Payment History
    if invoice.payments:
        elements.append(Paragraph("<b>Payment Transactions</b>", styles['Heading4']))
        pay_data = [[
            Paragraph("<b>Date</b>", meta_style),
            Paragraph("<b>Method</b>", meta_style),
            Paragraph("<b>Ref #</b>", meta_style),
            Paragraph("<b>Amount (PKR)</b>", meta_style)
        ]]
        for p in invoice.payments:
            pay_data.append([
                Paragraph(p_text(p.payment_date), meta_style),
                Paragraph(p_text(p.payment_method.name if p.payment_method else "Cash"), meta_style),
                Paragraph(p_text(p.transaction_reference or "N/A"), meta_style),
                Paragraph(f"PKR {float(p.amount):,.2f}", meta_style)
            ])
        p_table = Table(pay_data, colWidths=[120, 140, 140, 140])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(p_table)
        elements.append(Spacer(1, 15))

    footer_text = Paragraph(
        "<i>Thank you for working out with Titan Fitness! For queries, contact support@titanfitness.pk.</i>",
        styles['Italic']
    )
    elements.append(footer_text)
    doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()

def generate_revenue_report_pdf(month, year, invoices, expenses):
    """Generate Monthly Financial Revenue & Expense Report PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0d6efd')
    )
    meta_style = ParagraphStyle(
        'RepMeta',
        parent=styles['Normal'],
        fontSize=9,
        leading=12
    )

    total_revenue = sum(float(inv.total_amount) for inv in invoices)
    total_collected = sum(float(inv.paid_amount) for inv in invoices)
    total_outstanding = max(0.0, total_revenue - total_collected)
    total_expenses = sum(float(exp.amount) for exp in expenses)
    net_profit = total_collected - total_expenses

    elements = [
        Paragraph("<b>TITAN FITNESS - FINANCIAL REVENUE REPORT</b>", title_style),
        Paragraph(f"Period: {p_text(month)} / {p_text(year)} | Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles['Heading4']),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=12),
    ]

    summary_data = [
        [Paragraph("<b>Metric</b>", meta_style), Paragraph("<b>Amount (PKR)</b>", meta_style)],
        [Paragraph("Total Invoiced Amount", meta_style), Paragraph(f"PKR {total_revenue:,.2f}", meta_style)],
        [Paragraph("Total Cash Collected", meta_style), Paragraph(f"PKR {total_collected:,.2f}", meta_style)],
        [Paragraph("Total Outstanding Balance", meta_style), Paragraph(f"PKR {total_outstanding:,.2f}", meta_style)],
        [Paragraph("Total Operational Expenses", meta_style), Paragraph(f"PKR {total_expenses:,.2f}", meta_style)],
        [Paragraph("<b>Net Operating Cashflow</b>", meta_style), Paragraph(f"<b>PKR {net_profit:,.2f}</b>", meta_style)],
    ]
    sum_table = Table(summary_data, colWidths=[300, 240])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 16))

    # Top Invoices Table
    elements.append(Paragraph("<b>Recent Invoices in Period</b>", styles['Heading4']))
    inv_data = [[
        Paragraph("<b>Invoice #</b>", meta_style),
        Paragraph("<b>Member</b>", meta_style),
        Paragraph("<b>Date</b>", meta_style),
        Paragraph("<b>Total (PKR)</b>", meta_style),
        Paragraph("<b>Status</b>", meta_style),
    ]]
    for inv in invoices[:10]:
        inv_data.append([
            Paragraph(p_text(inv.invoice_number), meta_style),
            Paragraph(p_text(inv.member.full_name), meta_style),
            Paragraph(p_text(inv.issue_date), meta_style),
            Paragraph(f"{float(inv.total_amount):,.2f}", meta_style),
            Paragraph(p_text(inv.payment_status), meta_style)
        ])
    t_inv = Table(inv_data, colWidths=[100, 160, 90, 100, 90])
    t_inv.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_inv)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
