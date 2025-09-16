from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort
from app import db
from app.models import User, Doctor, Appointment
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models import MailSetting
import random
from flask import session
from app.models import User, MailSetting
import io
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from app.models import Appointment

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

patient_bp = Blueprint('patient', __name__, template_folder='templates')

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
    
    return render_template('patient/home.html', user_name=session.get('user_name'))

@patient_bp.route('/book-appointment')
def book_appointment():
    if 'user_id' not in session:
        flash('Please login to book an appointment.', 'warning')
        return redirect(url_for('patient.patient_login'))
    
    # Get all active and verified doctors
    doctors = Doctor.query.filter_by(is_active=True).all()
    return render_template('patient/book_appointment.html', 
                         doctors=doctors, 
                         user_name=session.get('user_name'))

from app.models import Payment

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
        appointment_time = request.form.get('appointment_time')
        razorpay_payment_id = request.form.get('razorpay_payment_id')
        razorpay_order_id = request.form.get('razorpay_order_id')
        razorpay_signature = request.form.get('razorpay_signature')
        amount = request.form.get('amount', 0)
        reason = request.form.get('reason')

        if not doctor_id or not appointment_date or not appointment_time or not razorpay_payment_id:
            if is_ajax:
                return jsonify(success=False, message="Missing appointment or payment details.")
            flash("Please provide all appointment and payment details.", "danger")
            return redirect(url_for('patient.book_appointment'))

        # Convert to datetime
        appointment_datetime = datetime.strptime(
            f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M"
        )

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
            appointment_time=appointment_datetime.time(),
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
    
    # Get all appointments for the current user
    appointments = Appointment.query.filter_by(patient_id=session['user_id'])\
                                  .order_by(Appointment.appointment_date.desc(), 
                                          Appointment.appointment_time.desc()).all()
    
    return render_template('patient/my_appointments.html', 
                         appointments=appointments,
                         user_name=session.get('user_name'))

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

    patient = User.query.get(session['user_id'])
    return render_template('patient/my_profile.html', patient=patient)


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
