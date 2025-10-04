from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort, make_response
from app import db
from app.models import User, Doctor, Appointment, MedicalPrescription,PatientIntakeForm, MailSetting, Payment, Specialization
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from sqlalchemy.orm import joinedload
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from flask import send_file

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

patient_bp = Blueprint('patient', __name__, template_folder='templates')

@patient_bp.route('/timeline/download-report')
def download_timeline_report():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    patient_id = session['user_id']
    appointments = Appointment.query.options(
        joinedload(Appointment.doctor).joinedload(Doctor.specialization),
        joinedload(Appointment.prescriptions).joinedload(MedicalPrescription.medicines)
    ).filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=50, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#0d6efd"), alignment=1)
    section_title = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#0d6efd"), spaceAfter=8, spaceBefore=16)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#495057"), leftIndent=0, spaceAfter=2)
    value_style = ParagraphStyle("Value", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#212529"), leftIndent=0, spaceAfter=6)

    # Header
    elements.append(Paragraph("Patient Timeline Report", header_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("HelthCare+ | www.healthcareplus.com", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Timeline visual design
    for idx, appt in enumerate(appointments):
        # Draw a card-like box for each appointment
        card = []
        card.append(Paragraph(f"<b>Date:</b> <font color='#0d6efd'>{appt.appointment_date.strftime('%d %b %Y')} {appt.appointment_time.strftime('%I:%M %p') if appt.appointment_time else ''}</font>", label_style))
        card.append(Paragraph(f"<b>Status:</b> <font color='#17a2b8'>{appt.status.capitalize()}</font>", value_style))
        card.append(Paragraph(f"<b>Doctor:</b> Dr. {appt.doctor.full_name} ({appt.doctor.specialization.name if appt.doctor.specialization else 'N/A'})", value_style))
        card.append(Paragraph(f"<b>Department:</b> {appt.doctor.specialization.name if appt.doctor.specialization else 'N/A'}", value_style))
        card.append(Paragraph(f"<b>Reason:</b> {appt.reason or 'N/A'}", value_style))
        if appt.prescriptions:
            pres = appt.prescriptions[0]
            card.append(Paragraph(f"<b>Prescription Date:</b> <font color='#198754'>{pres.created_at.strftime('%d %b %Y')}</font>", value_style))
            if pres.instructions:
                card.append(Paragraph(f"<b>Instructions:</b> {pres.instructions}", value_style))
            if pres.medicines:
                data = [["Name", "Type", "Dosage", "Frequency", "Days", "Timing", "Quantity", "Notes"]]
                for med in pres.medicines:
                    data.append([
                        med.name, med.type, med.dosage, med.frequency,
                        med.days, med.timing, med.quantity or "-", med.notes or "-"
                    ])
                table = Table(data, repeatRows=1, colWidths=[1.2*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.9*inch, 0.9*inch, 1.2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0d6efd")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
                ]))
                card.append(table)
        # Card border and spacing
        card_box = Table([[card]], colWidths=[6.5*inch])
        card_box.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor('#0d6efd')),
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('LEFTPADDING', (0,0), (-1,-1), 16),
            ('RIGHTPADDING', (0,0), (-1,-1), 16),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        # Add timeline dot and vertical line using a Spacer and a colored circle (simulate visually)
        if idx > 0:
            elements.append(Spacer(1, 8))
            # Simulate vertical line between cards
            elements.append(Paragraph("<font color='#0d6efd'>|</font>", ParagraphStyle('Line', fontSize=18, alignment=1)))
            elements.append(Spacer(1, 2))
        # Simulate timeline dot
        elements.append(Paragraph("<font color='#0d6efd'>&#9679;</font>", ParagraphStyle('Dot', fontSize=16, alignment=1)))
        elements.append(card_box)
        elements.append(Spacer(1, 10))

    # Only call doc.build once, after all elements are added
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Disposition'] = 'attachment; filename=patient_timeline_report.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response

@patient_bp.route('/intake-form', methods=['GET', 'POST'])
def patient_intake_form():
    if 'user_id' not in session:
        flash('Please log in to access the intake form.', 'warning')
        return redirect(url_for('patient.patient_login'))

    user_id_str = str(session['user_id'])
    form_data = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()

    # Check edit mode
    edit_mode = request.args.get("edit") == "1"

    if request.method == 'POST':
        if form_data:
            form_to_update = form_data
        else:
            form_to_update = PatientIntakeForm(
                created_by=user_id_str,
                registration_date=datetime.utcnow(),
                status='Active'
            )

        for key, value in request.form.items():
            if not value:
                value = None
            if key == 'consent_form_signed':
                setattr(form_to_update, key, True if value == "1" else False)
                continue
            if hasattr(form_to_update, key):
                setattr(form_to_update, key, value)

        if 'consent_form_signed' not in request.form:
            form_to_update.consent_form_signed = False

        try:
            if not form_data:
                db.session.add(form_to_update)
            db.session.commit()
            flash('Your information has been saved successfully!', 'success')
            return redirect(url_for('patient.my_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred. Please try again. Error: {e}', 'danger')

    return render_template('patient/intake_form_wizard.html', form=form_data, edit_mode=edit_mode)

@patient_bp.route('/intake-form/download-pdf')
def download_intake_form_pdf():
    if 'user_id' not in session:
        flash('Please log in to access the intake form.', 'warning')
        return redirect(url_for('patient.patient_login'))

    user_id_str = str(session['user_id'])
    form = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()
    if not form:
        flash('No intake form found.', 'danger')
        return redirect(url_for('patient.patient_intake_form'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=90, bottomMargin=60)
    elements = []
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#0d6efd"), alignment=1)
    section_title = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#0d6efd"), spaceAfter=8, spaceBefore=16)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#495057"), leftIndent=0, spaceAfter=2)
    value_style = ParagraphStyle("Value", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#212529"), leftIndent=0, spaceAfter=6)

    # Header
    elements.append(Paragraph("Patient Intake Form Report", header_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("HelthCare+ | www.healthcareplus.com", styles["Normal"]))
    elements.append(Spacer(1, 12))

    def add_field(label, value):
        elements.append(Paragraph(f"<b>{label}:</b>", label_style))
        elements.append(Paragraph(str(value) if value else "-", value_style))

    # Personal Information
    elements.append(Paragraph("Personal Information", section_title))
    add_field("First Name", form.first_name)
    add_field("Last Name", form.last_name)
    add_field("Date of Birth", form.date_of_birth.strftime('%Y-%m-%d') if form.date_of_birth else "")
    add_field("Age", form.age)
    add_field("Gender", form.gender)
    add_field("Blood Group", form.blood_group)
    add_field("National ID", form.national_id)
    add_field("Marital Status", form.marital_status)
    add_field("Occupation", form.occupation)
    add_field("Education Level", form.education_level)
    add_field("Language Preference", form.language_preference)

    # Contact Details
    elements.append(Paragraph("Contact Details", section_title))
    add_field("Phone Number", form.phone_number)
    add_field("Alternate Phone", form.alternate_phone)
    add_field("Email Address", form.email_address)
    add_field("Permanent Address", form.permanent_address)
    add_field("Current Address", form.current_address)
    add_field("Emergency Contact Name", form.emergency_contact_name)
    add_field("Emergency Contact Relationship", form.emergency_contact_relationship)
    add_field("Emergency Contact Phone", form.emergency_contact_phone)

    # Insurance Information
    elements.append(Paragraph("Insurance Information", section_title))
    add_field("Insurance Provider", form.insurance_provider)
    add_field("Policy Number", form.insurance_policy_number)
    add_field("Coverage Details", form.coverage_details)
    add_field("Validity Period", form.validity_period)
    add_field("Primary Policy Holder", form.primary_policy_holder)

    # Medical History
    elements.append(Paragraph("Medical History", section_title))
    add_field("Allergies", form.allergies)
    add_field("Past Illnesses", form.past_illnesses)
    add_field("Past Surgeries", form.past_surgeries)
    add_field("Current Medications", form.current_medications)
    add_field("Family History", form.family_history)
    add_field("Vaccination Status", form.vaccination_status)
    add_field("Chronic Conditions", form.chronic_conditions)

    # Lifestyle & Social History
    elements.append(Paragraph("Lifestyle & Social History", section_title))
    add_field("Smoking Status", form.smoking_status)
    add_field("Alcohol Use", form.alcohol_use)
    add_field("Drug Use", form.drug_use)
    add_field("Exercise Habits", form.exercise_habits)
    add_field("Diet Pattern", form.diet_pattern)
    add_field("Sleep Pattern", form.sleep_pattern)
    add_field("Stress Level", form.stress_level)

    # Reproductive / OB-GYN History
    elements.append(Paragraph("Reproductive / OB-GYN History", section_title))
    add_field("Menstrual Cycle", form.menstrual_cycle)
    add_field("Last Menstrual Period", form.last_menstrual_period.strftime('%Y-%m-%d') if form.last_menstrual_period else "")
    add_field("Pregnancy Status", form.pregnancy_status)
    add_field("Number of Pregnancies", form.number_of_pregnancies)
    add_field("Number of Children", form.number_of_children)
    add_field("Contraceptive Use", form.contraceptive_use)

    # Visit / Clinical Data
    elements.append(Paragraph("Visit / Clinical Data", section_title))
    add_field("Reason for Visit", form.reason_for_visit)
    add_field("Symptoms", form.symptoms)
    add_field("Diagnosis", form.diagnosis)
    add_field("Treatment Plan", form.treatment_plan)
    add_field("Doctor Assigned", form.doctor_assigned)
    add_field("Visit Date", form.visit_date.strftime('%Y-%m-%d') if form.visit_date else "")
    add_field("Next Appointment Date", form.next_appointment_date.strftime('%Y-%m-%d') if form.next_appointment_date else "")

    # Consent & Legal
    elements.append(Paragraph("Consent & Legal", section_title))
    add_field("Consent Form Signed", "Yes" if form.consent_form_signed else "No")
    add_field("Consent Date", form.consent_date.strftime('%Y-%m-%d') if form.consent_date else "")
    add_field("Legal Guardian Name", form.legal_guardian_name)
    add_field("Guardian Relationship", form.guardian_relationship)
    add_field("Guardian Signature", form.guardian_signature)

    # Administrative
    elements.append(Paragraph("Administrative", section_title))
    add_field("Registration Date", form.registration_date.strftime('%Y-%m-%d %H:%M') if form.registration_date else "")
    add_field("Created By", form.created_by)
    add_field("Last Updated", form.last_updated.strftime('%Y-%m-%d %H:%M') if form.last_updated else "")
    add_field("Status", form.status)

    # Footer (on every page)
    def add_footer(canvas, doc):
        width, height = letter
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#0d6efd"))
        canvas.setLineWidth(0.5)
        canvas.line(40, 50, width - 40, 50)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.gray)
        canvas.drawCentredString(width / 2, 35, "HelthCare+ | www.healthcareplus.com | +91 98765 43210")
        canvas.drawRightString(width - 40, 20, f"Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"intake_form_{form.id}.pdf",
        mimetype="application/pdf"
    )

@patient_bp.route('/login')
def patient_login():
    return render_template('patient/auth.html')

@patient_bp.route('/login', methods=['POST'])
def patient_login_post():
    if request.form.get('form_type') != 'login':
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('patient.patient_login'))

    mobile_number = clean_mobile_number(request.form['mobile_number'])
    password = request.form['password']

    user = User.query.filter_by(mobile_number=mobile_number).first()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_name'] = user.full_name
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect(url_for('patient.patient_home'))
    else:
        flash('Invalid mobile number or password', 'danger')
        return render_template('patient/auth.html')


@patient_bp.route('/signup', methods=['POST'])
def patient_signup():
    print("________")
    print("REQUEST FORM", request.form)
    print("________")

    # Defensive coding to avoid crashing
    if request.form.get('form_type') != 'signup':
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('patient.patient_login'))

    full_name = request.form.get('full_name')
    mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
    email = request.form.get('email', '')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not full_name or not mobile_number or not password or not confirm_password:
        flash('All required fields must be filled.', 'danger')
        return render_template('patient/auth.html')

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('patient/auth.html')

    existing_user = User.query.filter_by(mobile_number=mobile_number).first()
    if existing_user:
        flash('Mobile number already registered.', 'danger')
        return render_template('patient/auth.html')

    hashed_password = generate_password_hash(password)
    new_user = User(
        full_name=full_name,
        mobile_number=mobile_number,
        email=email if email else None,
        password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    flash('Account created successfully! Please login.', 'success')
    return render_template('patient/auth.html')


@patient_bp.route('/home')
def patient_home():
    if 'user_id' not in session:
        flash('Please login to access this page.', 'warning')
        return redirect(url_for('patient.patient_login'))
    
    # Intake form prompt logic
    show_intake_prompt = False
    if 'user_id' in session:
        from app.models import PatientIntakeForm
        user_id_str = str(session['user_id'])
        intake_form = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()
        if not intake_form:
            show_intake_prompt = True
    return render_template('patient/home.html', user_name=session.get('user_name'), show_intake_prompt=show_intake_prompt)

@patient_bp.route('/book-appointment')
def book_appointment():
    if 'user_id' not in session:
        flash('Please login to book an appointment.', 'warning')
        return redirect(url_for('patient.patient_login'))
    # Intake form prompt logic
    show_intake_prompt = False
    if 'user_id' in session:
        from app.models import PatientIntakeForm
        user_id_str = str(session['user_id'])
        intake_form = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()
        if not intake_form:
            show_intake_prompt = True
    # Get all specializations
    from app.models import Specialization
    specializations = Specialization.query.all()
    specialization_id = request.args.get('specialization_id', type=int)
    doctors = []
    if specialization_id:
        doctors = Doctor.query.filter_by(is_active=True, specialization_id=specialization_id).all()
    return render_template('patient/book_appointment.html', 
                         doctors=doctors, 
                         specializations=specializations,
                         selected_specialization_id=specialization_id,
                         user_name=session.get('user_name'),
                         show_intake_prompt=show_intake_prompt)
@patient_bp.route('/get-doctors-by-specialization', methods=['GET'])
def get_doctors_by_specialization():
    specialization_id = request.args.get('specialization_id', type=int)
    doctors = []
    if specialization_id:
        doctors = Doctor.query.filter_by(is_active=True, specialization_id=specialization_id).all()
    doctor_list = [
        {
            'id': doctor.id,
            'full_name': doctor.full_name,
            'specialization': doctor.specialization.name if doctor.specialization else '',
            'experience_years': doctor.experience_years,
            'qualification': doctor.qualification,
            'hospital_affiliation': doctor.hospital_affiliation
        }
        for doctor in doctors
    ]
    return jsonify({'doctors': doctor_list})

from app.models import Payment

# @patient_bp.route('/book-appointment', methods=['POST'])
# def book_appointment_post():
#     """Handle booking an appointment after Razorpay payment success."""
#     is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

#     if 'user_id' not in session:
#         if is_ajax:
#             return jsonify(success=False, message="Please login to book an appointment.")
#         flash('Please login to book an appointment.', 'warning')
#         return redirect(url_for('patient.patient_login'))

#     try:
#         doctor_id = request.form.get('doctor_id')
#         appointment_date = request.form.get('appointment_date')
#         appointment_time = request.form.get('appointment_time')
#         razorpay_payment_id = request.form.get('razorpay_payment_id')
#         razorpay_order_id = request.form.get('razorpay_order_id')
#         razorpay_signature = request.form.get('razorpay_signature')
#         amount = request.form.get('amount', 0)
#         reason = request.form.get('reason')

#         if not doctor_id or not appointment_date or not appointment_time or not razorpay_payment_id:
#             if is_ajax:
#                 return jsonify(success=False, message="Missing appointment or payment details.")
#             flash("Please provide all appointment and payment details.", "danger")
#             return redirect(url_for('patient.book_appointment'))

#         # Convert to datetime
#         appointment_datetime = datetime.strptime(
#             f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M"
#         )

#         patient = User.query.get(session['user_id'])
#         doctor = Doctor.query.get(doctor_id)

#         if not doctor or not patient:
#             if is_ajax:
#                 return jsonify(success=False, message="Invalid doctor or patient.")
#             flash("Invalid doctor or patient.", "danger")
#             return redirect(url_for('patient.book_appointment'))

#         # Create appointment
#         appointment = Appointment(
#             doctor_id=doctor.id,
#             patient_id=patient.id,
#             patient_name=patient.full_name,
#             appointment_date=appointment_datetime.date(),
#             appointment_time=appointment_datetime.time(),
#             status="scheduled",
#             reason=reason
#         )
#         db.session.add(appointment)
#         db.session.commit()

#         # Save payment record
#         payment = Payment(
#             appointment_id=appointment.id,
#             razorpay_payment_id=razorpay_payment_id,
#             amount=float(amount),
#             currency='INR',
#             status='success'
#         )
#         db.session.add(payment)
#         db.session.commit()

#         # Send appointment confirmation email
#         if patient.email:
#             send_appointment_email(
#                 patient_email=patient.email,
#                 patient_name=patient.full_name,
#                 doctor_name=f"Dr. {doctor.full_name}",
#                 appointment_date=appointment.appointment_date.strftime('%d %B %Y'),
#                 appointment_time=appointment.appointment_time.strftime('%I:%M %p'),
#                 reason=reason
#             )

#         if is_ajax:
#             return jsonify(success=True, redirect_url=url_for('patient.my_appointments'))

#         flash("Appointment booked and payment recorded successfully!", "success")
#         return redirect(url_for('patient.my_appointments'))

#     except Exception as e:
#         db.session.rollback()
#         print("Error while booking appointment:", str(e))
#         if is_ajax:
#             return jsonify(success=False, message="An error occurred while booking your appointment.")
#         flash("An error occurred while booking the appointment. Please try again.", "danger")
#         return redirect(url_for('patient.book_appointment'))

@patient_bp.route('/book-appointment', methods=['POST'])
def book_appointment_post():
    """Handle booking an appointment after Razorpay payment success."""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if 'user_id' not in session:
        if is_ajax:
            return jsonify(success=False, message="Please login to book an appointment.")
        flash('Please login to book an appointment.', 'warning')
        return redirect(url_for('patient.patient_login'))

    try:
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        razorpay_payment_id = request.form.get('razorpay_payment_id')
        razorpay_order_id = request.form.get('razorpay_order_id')
        razorpay_signature = request.form.get('razorpay_signature')
        amount = request.form.get('amount', 0)
        reason = request.form.get('reason')

        # Debug logging
        print(f"Received form data: doctor_id={doctor_id}, date={appointment_date}")
        print(f"Payment data: payment_id={razorpay_payment_id}")

        if not doctor_id or not appointment_date or not razorpay_payment_id:
            if is_ajax:
                return jsonify(success=False, message="Missing appointment or payment details.")
            flash("Please provide all appointment and payment details.", "danger")
            return redirect(url_for('patient.book_appointment'))

        # Convert to datetime - use a default time (e.g., 10:00 AM)
        appointment_datetime = datetime.strptime(appointment_date, "%Y-%m-%d")
        default_time = time(10, 0)  # 10:00 AM as default

        patient = User.query.get(session['user_id'])
        doctor = Doctor.query.get(doctor_id)

        if not doctor or not patient:
            if is_ajax:
                return jsonify(success=False, message="Invalid doctor or patient.")
            flash("Invalid doctor or patient.", "danger")
            return redirect(url_for('patient.book_appointment'))

        # Create appointment
        appointment = Appointment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            patient_name=patient.full_name,
            appointment_date=appointment_datetime.date(),
            appointment_time=default_time,  # Use default time
            status="scheduled",
            reason=reason
        )
        db.session.add(appointment)
        db.session.commit()

        # Save payment record
        payment = Payment(
            appointment_id=appointment.id,
            razorpay_payment_id=razorpay_payment_id,
            amount=float(amount),
            currency='INR',
            status='success'
        )
        db.session.add(payment)
        db.session.commit()

        # Send appointment confirmation email
        if patient.email:
            send_appointment_email(
                patient_email=patient.email,
                patient_name=patient.full_name,
                doctor_name=f"Dr. {doctor.full_name}",
                appointment_date=appointment.appointment_date.strftime('%d %B %Y'),
                appointment_time=appointment.appointment_time.strftime('%I:%M %p'),
                reason=reason
            )

        if is_ajax:
            return jsonify(success=True, redirect_url=url_for('patient.my_appointments'))

        flash("Appointment booked and payment recorded successfully!", "success")
        return redirect(url_for('patient.my_appointments'))

    except Exception as e:
        db.session.rollback()
        print("Error while booking appointment:", str(e))
        if is_ajax:
            return jsonify(success=False, message="An error occurred while booking your appointment.")
        flash("An error occurred while booking the appointment. Please try again.", "danger")
        return redirect(url_for('patient.book_appointment'))

@patient_bp.route('/my-appointments')
def my_appointments():
    if 'user_id' not in session:
        flash('Please login to view your appointments.', 'warning')
        return redirect(url_for('patient.patient_login'))
    # Intake form prompt logic
    show_intake_prompt = False
    if 'user_id' in session:
        from app.models import PatientIntakeForm
        user_id_str = str(session['user_id'])
        intake_form = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()
        if not intake_form:
            show_intake_prompt = True
    # Get all appointments for the current user
    appointments = Appointment.query.filter_by(patient_id=session['user_id'])\
                                  .order_by(Appointment.appointment_date.desc(), 
                                          Appointment.appointment_time.desc()).all()

    # Compute display status for each appointment
    today = datetime.utcnow().date()
    for appt in appointments:
        if appt.status == 'cancelled':
            appt.display_status = 'Cancelled'
        elif appt.status == 'completed':
            appt.display_status = 'Appointment Done'
        elif appt.appointment_date == today:
            appt.display_status = 'Today Scheduled'
        elif appt.status == 'scheduled':
            appt.display_status = 'Appointment Booked'
        else:
            appt.display_status = appt.status.capitalize()

    return render_template('patient/my_appointments.html', 
                         appointments=appointments,
                         user_name=session.get('user_name'),
                         show_intake_prompt=show_intake_prompt)

@patient_bp.route('/cancel-appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Please login to cancel appointments.', 'warning')
        return redirect(url_for('patient.patient_login'))
    
    appointment = Appointment.query.filter_by(
        id=appointment_id, 
        patient_id=session['user_id']
    ).first()
    
    if not appointment:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('patient.my_appointments'))
    
    if appointment.status == 'cancelled':
        flash('Appointment is already cancelled.', 'warning')
        return redirect(url_for('patient.my_appointments'))
    
    appointment.status = 'cancelled'
    appointment.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('patient.my_appointments'))

@patient_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@patient_bp.route('/my-profile')
def my_profile():
    if 'user_id' not in session:
        flash('Please login to view your profile.', 'warning')
        return redirect(url_for('patient.patient_login'))
    # Intake form prompt logic
    show_intake_prompt = False
    if 'user_id' in session:
        from app.models import PatientIntakeForm
        user_id_str = str(session['user_id'])
        intake_form = PatientIntakeForm.query.filter_by(created_by=user_id_str).first()
        if not intake_form:
            show_intake_prompt = True
    patient = User.query.get(session['user_id'])
    return render_template('patient/my_profile.html', patient=patient, show_intake_prompt=show_intake_prompt)

@patient_bp.route('/timeline')
def patient_timeline():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    patient_id = session['user_id']
    appointments = Appointment.query.options(
        joinedload(Appointment.doctor).joinedload(Doctor.specialization),
        joinedload(Appointment.prescriptions).joinedload(MedicalPrescription.medicines)
    ).filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()

    return render_template('patient/patient_timeline.html', appointments=appointments)

@patient_bp.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash('Please login to update your profile.', 'warning')
        return redirect(url_for('patient.patient_login'))

    patient = User.query.get(session['user_id'])
    if not patient:
        flash('User not found.', 'danger')
        return redirect(url_for('patient.my_profile'))

    # Store old info for email
    old_full_name = patient.full_name
    old_email = patient.email
    old_mobile = patient.mobile_number
    password_changed = False

    # Update fields
    patient.full_name = request.form.get('full_name')
    patient.email = request.form.get('email')
    patient.mobile_number = request.form.get('mobile_number')

    password = request.form.get('password')
    if password:  # only update if new password entered
        patient.password = generate_password_hash(password)
        password_changed = True
        new_password = password  # store the actual new password to send in email
    else:
        new_password = None


    db.session.commit()
    session['user_name'] = patient.full_name  # keep session in sync

    # Send profile update email
    send_profile_update_email(
        patient,
        old_full_name=old_full_name,
        old_email=old_email,
        old_mobile=old_mobile,
        password_changed=password_changed,
        new_password=new_password
    )

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('patient.my_profile'))


def send_profile_update_email(patient, old_full_name, old_email, old_mobile, password_changed=False, new_password=None):
    from app.models import MailSetting

    mail_config = MailSetting.query.first()
    if not mail_config:
        print("Mail settings not configured!")
        return

    sender_email = mail_config.mail_default_email or mail_config.mail_username
    receiver_email = patient.email
    if not receiver_email:
        return

    html_content = render_template(
        'email/profile_update.html',
        full_name=patient.full_name,
        email=patient.email,
        mobile_number=patient.mobile_number,
        old_full_name=old_full_name,
        old_email=old_email,
        old_mobile=old_mobile,
        password_changed=password_changed,
        new_password=new_password
    )


    msg = MIMEMultipart("alternative")
    msg['Subject'] = "Your Profile Has Been Updated"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(mail_config.mail_server, mail_config.mail_port) as server:
            if mail_config.mail_use_tls:
                server.starttls()
            server.login(mail_config.mail_username, mail_config.mail_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"Profile update email sent to {receiver_email}")
    except Exception as e:
        print("Failed to send email:", e)


@patient_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    step = 'enter_number'
    
    if request.method == 'POST':
        # Step 1: Send verification code
        if 'mobile_number' in request.form and 'verification_code' not in request.form and 'password' not in request.form:
            mobile_number = clean_mobile_number(request.form['mobile_number'])
            user = User.query.filter_by(mobile_number=mobile_number).first()
            if not user:
                flash('This mobile number is not registered.', 'danger')
                return render_template('patient/forgot_password.html', step='enter_number')

            # Generate 6-digit code
            code = '{:06d}'.format(random.randint(0, 999999))
            session['forgot_password_code'] = code
            session['forgot_password_mobile'] = mobile_number

            # Send email
            send_forgot_password_email(user.email, user.full_name, code)

            flash('A 6-digit verification code has been sent to your registered email.', 'info')
            return render_template('patient/forgot_password.html', step='enter_code', mobile_number=mobile_number)

        # Step 2: Verify code
        elif 'verification_code' in request.form:
            mobile_number = clean_mobile_number(request.form['mobile_number'])
            entered_code = request.form['verification_code']
            code = session.get('forgot_password_code')
            mobile_session = session.get('forgot_password_mobile')

            if code != entered_code or mobile_number != mobile_session:
                flash('Invalid verification code.', 'danger')
                return render_template('patient/forgot_password.html', step='enter_code', mobile_number=mobile_number)

            flash('Code verified. Enter your new password.', 'info')
            return render_template('patient/forgot_password.html', step='reset_password', mobile_number=mobile_number)

        # Step 3: Update password
        elif 'password' in request.form:
            mobile_number = clean_mobile_number(request.form['mobile_number'])
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('patient/forgot_password.html', step='reset_password', mobile_number=mobile_number)

            user = User.query.filter_by(mobile_number=mobile_number).first()
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('patient.patient_login'))

            from werkzeug.security import generate_password_hash
            user.password = generate_password_hash(password)
            db.session.commit()

            # Clear session codes
            session.pop('forgot_password_code', None)
            session.pop('forgot_password_mobile', None)

            flash('Password updated successfully! Please login.', 'success')
            return redirect(url_for('patient.patient_login'))

    return render_template('patient/forgot_password.html', step=step)


def send_forgot_password_email(receiver_email, full_name, code):
    mail_config = MailSetting.query.first()
    if not mail_config or not receiver_email:
        print("Mail settings missing or email not available!")
        return

    sender_email = mail_config.mail_default_email or mail_config.mail_username

    html_content = render_template(
        'email/forgot_password.html',
        full_name=full_name,
        code=code
    )

    msg = MIMEMultipart("alternative")
    msg['Subject'] = "Your Password Reset Code"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(mail_config.mail_server, mail_config.mail_port) as server:
            if mail_config.mail_use_tls:
                server.starttls()
            server.login(mail_config.mail_username, mail_config.mail_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("\n\n\n")
        print(f"Forgot password code sent to {receiver_email}")
        print("\n\n\n")
    except Exception as e:
        print('\n\n\n')
        print("Failed to send email:", e)
        print('\n\n\n')

import io
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from app.models import Appointment

@patient_bp.route('/appointments/<int:appointment_id>/download')
def download_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # ---------------- HEADER ----------------
    c.setFillColor(colors.HexColor("#007BFF"))
    c.rect(0, height - 80, width, 80, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(70, height - 50, "HelthCare+")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 40, "Your Health, Our Priority")

    # ---------------- TITLE ----------------
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 120, "Appointment Details")

    # ---------------- DETAILS ----------------
    y = height - 170
    line_height = 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Appointment ID:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, str(appointment.id))

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Patient Name:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, appointment.user.full_name)   # Assuming relation with User model

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Doctor:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, f"Dr. {appointment.doctor.full_name}")

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Specialization:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, appointment.doctor.specialization)

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Date:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, appointment.appointment_date.strftime('%d %B %Y'))

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Time:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, appointment.appointment_time.strftime('%I:%M %p'))

    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(80, y, "Status:")
    c.setFont("Helvetica", 12)
    c.drawString(200, y, appointment.status.capitalize())

    if appointment.reason:
        y -= line_height
        c.setFont("Helvetica-Bold", 12)
        c.drawString(80, y, "Reason:")
        c.setFont("Helvetica", 12)
        c.drawString(200, y, appointment.reason)

    # ---------------- FOOTER ----------------
    c.setStrokeColor(colors.HexColor("#007BFF"))
    c.setLineWidth(0.5)
    c.line(40, 50, width - 40, 50)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 35, "HelthCare+ | www.healthcareplus.com | +91 98765 43210")
    c.drawRightString(width - 40, 20, f"Page 1")

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"appointment_{appointment.id}.pdf",
        mimetype="application/pdf"
    )

def send_appointment_email(patient_email, patient_name, doctor_name, appointment_date, appointment_time):
    # Get mail config from database (latest one)
    mail_config = MailSetting.query.order_by(MailSetting.updated_at.desc()).first()
    if not mail_config:
        print("No mail configuration found!")
        return False

    try:
        # Email content
        subject = "Appointment Confirmation - HMS"
        body = f"""
        Dear {patient_name},

        Your appointment has been successfully booked.

        Doctor: {doctor_name}
        Date: {appointment_date}
        Time: {appointment_time}

        Thank you for choosing HMS.

        Regards,
        {mail_config.mail_default_name or "HMS Team"}
        """

        # Setup email message
        msg = MIMEMultipart()
        msg["From"] = f"{mail_config.mail_default_name} <{mail_config.mail_default_email}>"
        msg["To"] = patient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server
        server = smtplib.SMTP(mail_config.mail_server, mail_config.mail_port)
        if mail_config.mail_use_tls:
            server.starttls()
        server.login(mail_config.mail_username, mail_config.mail_password)

        # Send mail
        server.sendmail(mail_config.mail_default_email, patient_email, msg.as_string())
        server.quit()
        print("Mail sent successfully")
        return True
    except Exception as e:
        print(f"Error sending mail: {e}")
        return False


from flask import render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models import MailSetting

def send_appointment_email(patient_email, patient_name, doctor_name, appointment_date, appointment_time, reason=None):
    # Fetch mail settings
    mail_config = MailSetting.query.order_by(MailSetting.updated_at.desc()).first()
    if not mail_config:
        print("No mail configuration found!")
        return False

    try:
        # Render HTML email from template
        html_body = render_template(
            'email/appointment_email.html',
            patient_name=patient_name,
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            mail_default_name=mail_config.mail_default_name or "HMS Team"
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{mail_config.mail_default_name} <{mail_config.mail_default_email}>"
        msg["To"] = patient_email
        msg["Subject"] = "Appointment Confirmation - HMS"
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(mail_config.mail_server, mail_config.mail_port)
        if mail_config.mail_use_tls:
            server.starttls()
        server.login(mail_config.mail_username, mail_config.mail_password)
        server.sendmail(mail_config.mail_default_email, patient_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
        return True

    except Exception as e:
        print(f"Error sending mail: {e}")
        return False


@patient_bp.route('/check-appointment-availability')
# @patient_required
def check_appointment_availability():
    doctor_id = request.args.get('doctor_id')
    date_str = request.args.get('date')
    
    if not doctor_id or not date_str:
        return jsonify({'available': False, 'message': 'Missing parameters'})
    
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({'available': False, 'message': 'Doctor not found'})
        
        # Parse date
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Count appointments for this doctor on the selected date
        appointment_count = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()
        
        # Check if doctor has reached daily limit
        if appointment_count >= doctor.appointments_per_day:
            return jsonify({
                'available': False, 
                'message': f'This doctor has no available appointments on {date_str}.'
            })
        
        return jsonify({
            'available': True,
            'message': f'Appointment available on {date_str}.'
        })
        
    except Exception as e:
        return jsonify({'available': False, 'message': f'Error checking availability: {str(e)}'})

@patient_bp.route('/medical-records')
def medical_records():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    patient_id = session['user_id']
    appointments = Appointment.query.options(
        joinedload(Appointment.prescriptions).joinedload(MedicalPrescription.medicines)
    ).filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).all()

    return render_template('patient/medical_records.html', appointments=appointments)


@patient_bp.route('/medical-records/download/<int:appointment_id>')
def download_prescription_pdf(appointment_id):
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))

    appointment = Appointment.query.options(
        joinedload(Appointment.prescriptions).joinedload(MedicalPrescription.medicines)
    ).filter_by(id=appointment_id, patient_id=session['user_id']).first()

    if not appointment:
        flash("Appointment not found or unauthorized.", "danger")
        return redirect(url_for('patient.medical_records'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=50, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle("Header", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#007BFF"), alignment=1)
    subheader_style = ParagraphStyle("Subheader", parent=styles["Heading2"], fontSize=12, textColor=colors.black, spaceAfter=6)
    normal_bold = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=11, textColor=colors.black, leading=14, spaceAfter=6)

    elements.append(Paragraph("🏥 HelthCare+", header_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Appointment Date:</b> {appointment.appointment_date.strftime('%d-%b-%Y')} at {appointment.appointment_time.strftime('%I:%M %p') if appointment.appointment_time else ''}", subheader_style))
    elements.append(Paragraph(f"<b>Doctor:</b> Dr. {appointment.doctor.full_name}", subheader_style))
    elements.append(Paragraph(f"<b>Patient ID:</b> {appointment.patient_id}", subheader_style))
    elements.append(Spacer(1, 15))

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

    elements.append(Spacer(1, 40))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9, textColor=colors.grey, alignment=1)
    elements.append(Paragraph("HelthCare+ • Your Trusted Medical Partner", footer_style))
    elements.append(Paragraph("Contact: info@healthcareplus.com | +1 (555) 123-4567", footer_style))

    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Disposition'] = f'attachment; filename=appointment_{appointment.id}.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


@patient_bp.route('/payment-records')
def payment_records():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))
    
    # Get all payments for the current user through their appointments
    payments = Payment.query.join(Appointment).filter(
        Appointment.patient_id == session['user_id']
    ).order_by(Payment.created_at.desc()).all()
    
    return render_template('patient/payment_records.html', 
                         payments=payments,
                         user_name=session.get('user_name'))

@patient_bp.route('/payment-receipt/<int:payment_id>')
def download_payment_receipt(payment_id):
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('patient.patient_login'))
    
    # Verify the payment belongs to the current user
    payment = Payment.query.join(Appointment).filter(
        Payment.id == payment_id,
        Appointment.patient_id == session['user_id']
    ).first_or_404()
    
    # Create PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header with logo
    c.setFillColor(colors.HexColor("#007BFF"))
    c.rect(0, height - 80, width, 80, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(70, height - 50, "HelthCare+")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 40, "Your Health, Our Priority")
    
    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 120, "PAYMENT RECEIPT")
    
    # Payment details
    y = height - 160
    line_height = 20
    
    details = [
        ("Receipt Number:", payment.razorpay_payment_id),
        ("Payment Date:", payment.created_at.strftime('%d-%b-%Y %I:%M %p')),
        ("Amount:", f"{payment.amount:.2f}"),
        ("Status:", payment.status.upper()),
        ("Appointment ID:", str(payment.appointment.id)),
        ("Patient Name:", payment.appointment.patient_name),
        ("Doctor:", f"Dr. {payment.appointment.doctor.full_name}"),
        ("Appointment Date:", payment.appointment.appointment_date.strftime('%d-%b-%Y')),
        ("Appointment Time:", payment.appointment.appointment_time.strftime('%I:%M %p') if payment.appointment.appointment_time else 'N/A')
    ]
    
    c.setFont("Helvetica-Bold", 12)
    for label, value in details:
        c.drawString(80, y, label)
        c.setFont("Helvetica", 12)
        c.drawString(200, y, value)
        c.setFont("Helvetica-Bold", 12)
        y -= line_height
    
    # Footer
    c.setStrokeColor(colors.HexColor("#007BFF"))
    c.setLineWidth(0.5)
    c.line(40, 50, width - 40, 50)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 35, "HelthCare+ | www.healthcareplus.com | +91 98765 43210")
    c.drawRightString(width - 40, 20, f"Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"payment_receipt_{payment.razorpay_payment_id}.pdf",
        mimetype="application/pdf"
    )