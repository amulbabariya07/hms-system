from flask import Blueprint, render_template, session, flash, redirect, url_for
from app.models import MedicalPrescription, Appointment, Doctor, User
from app import db
from datetime import datetime
from sqlalchemy.orm import joinedload
from flask import make_response
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
import io



patient_medical_bp = Blueprint('patient_medical', __name__, template_folder='templates')

@patient_medical_bp.route('/medical-records')
def medical_records():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    patient_id = session['user_id']

    appointments = (
        Appointment.query
        .options(
            joinedload(Appointment.prescriptions)
            .joinedload(MedicalPrescription.medicines)
        )
        .filter_by(patient_id=patient_id)
        .order_by(Appointment.appointment_date.desc())
        .all()
    )

    return render_template('patient/medical_records.html', appointments=appointments)


@patient_medical_bp.route('/medical-records/download/<int:appointment_id>')
def download_prescription_pdf(appointment_id):
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    appointment = (
        Appointment.query
        .options(
            joinedload(Appointment.prescriptions)
            .joinedload(MedicalPrescription.medicines)
        )
        .filter_by(id=appointment_id, patient_id=session['user_id'])
        .first()
    )

    if not appointment:
        flash("Appointment not found or unauthorized.", "danger")
        return redirect(url_for('patient_medical.medical_records'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=50, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle("Header", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#007BFF"), alignment=1)
    subheader_style = ParagraphStyle("Subheader", parent=styles["Heading2"], fontSize=12, textColor=colors.black, spaceAfter=6)
    normal_bold = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=11, textColor=colors.black, leading=14, spaceAfter=6)

    # Hospital Header
    elements.append(Paragraph("🏥 HelthCare+", header_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Appointment Date:</b> {appointment.appointment_date.strftime('%d-%b-%Y')} at {appointment.appointment_time.strftime('%I:%M %p') if appointment.appointment_time else ''}", subheader_style))
    elements.append(Paragraph(f"<b>Doctor:</b> Dr. {appointment.doctor.full_name}", subheader_style))
    elements.append(Paragraph(f"<b>Patient ID:</b> {appointment.patient_id}", subheader_style))
    elements.append(Spacer(1, 15))

    # Prescriptions
    for pres in appointment.prescriptions:
        elements.append(Paragraph(f"📝 Prescription Date: {pres.created_at.strftime('%d-%b-%Y %I:%M %p')}", normal_bold))
        
        if pres.instructions:
            elements.append(Paragraph(f"<b>Instructions:</b> {pres.instructions}", styles["Normal"]))
            elements.append(Spacer(1, 8))

        if pres.medicines:
            data = [["Medicine", "Type", "Dosage", "Frequency", "Days", "Timing", "Quantity", "Notes"]]
            for med in pres.medicines:
                data.append([
                    med.name, med.type, med.dosage, med.frequency,
                    med.days, med.timing, med.quantity or "-", med.notes or "-"
                ])
            
            # Styled Table
            table = Table(data, repeatRows=1, colWidths=[1.2*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.9*inch, 0.9*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#007BFF")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

    # Footer
    elements.append(Spacer(1, 40))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9, textColor=colors.grey, alignment=1)
    elements.append(Paragraph("HelthCare+ • Your Trusted Medical Partner", footer_style))
    elements.append(Paragraph("Contact: info@healthcareplus.com | +91 8320269460", footer_style))

    doc.build(elements)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Disposition'] = f'attachment; filename=appointment_{appointment.id}.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response
