from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Payment, Appointment
from . import admin_bp

# Payment Records view
@admin_bp.route('/payment-records', methods=['GET'])
def admin_payment_records():
    search = request.args.get('search', '').strip()
    query = Payment.query.join(Appointment)
    if search:
        query = query.filter(Appointment.patient_name.ilike(f'%{search}%'))
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payment_records.html', payments=payments)


from flask import send_file
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch

@admin_bp.route('/download-receipt/<int:payment_id>', methods=['GET'])
def download_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    # Create an in-memory PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # 🧾 Optional: Add your clinic logo (if you have a file path)
    # logo_path = "app/static/images/logo.png"
    # elements.append(Image(logo_path, width=1.5*inch, height=1.5*inch))
    
    # Title
    title_style = ParagraphStyle(
        name="Title",
        fontSize=18,
        leading=22,
        alignment=1,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=20
    )
    elements.append(Paragraph("<b>Payment Receipt</b>", title_style))

    # Clinic Info Header
    header_style = ParagraphStyle(
        name="Header",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#555555"),
        alignment=1,
        spaceAfter=10
    )
    elements.append(Paragraph("Healthy Life Clinic", header_style))
    elements.append(Spacer(1, 15))

    # Horizontal line
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#3498db"), thickness=1))
    elements.append(Spacer(1, 20))

    # Payment details table
    data = [
        ["Payment ID:", f"#{payment.id}"],
        ["Patient Name:", payment.appointment.patient_name],
        ["Doctor Name:", payment.appointment.doctor.full_name],
        ["Amount (INR):", f"{payment.amount:,.2f}"],
        ["Status:", payment.status.capitalize()],
        ["Date & Time:", payment.created_at.strftime('%b %d, %Y, %I:%M %p')],
        ["Razorpay ID:", payment.razorpay_payment_id or "N/A"]
    ]

    table = Table(data, colWidths=[140, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6f7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 30))

    # Thank You Note
    thank_style = ParagraphStyle(
        name="ThankYou",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#16a085"),
        alignment=1,
        spaceBefore=20
    )
    elements.append(Paragraph("Thank you for your payment!", thank_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("We appreciate your trust in Healthy Life Clinic.", styles["Normal"]))

    # Footer
    footer_style = ParagraphStyle(
        name="Footer",
        fontSize=9,
        alignment=1,
        textColor=colors.HexColor("#7f8c8d"),
        spaceBefore=40
    )
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("This is a computer-generated receipt and does not require a signature.", footer_style))

    # Build PDF
    doc.build(elements)

    buffer.seek(0)
    filename = f"receipt_{payment.id}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
