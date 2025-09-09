from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User, Doctor, Appointment
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models import MailSetting

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

@patient_bp.route('/book-appointment', methods=['POST'])
def book_appointment_post():
    if 'user_id' not in session:
        flash('Please login to book an appointment.', 'warning')
        return redirect(url_for('patient.patient_login'))
    

    try:
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason', '')

        # Payment info from Razorpay
        razorpay_payment_id = request.form.get('razorpay_payment_id')
        razorpay_order_id = request.form.get('razorpay_order_id')
        razorpay_signature = request.form.get('razorpay_signature')
        amount = request.form.get('amount')

        # Validation
        if not all([doctor_id, appointment_date, appointment_time, razorpay_payment_id, razorpay_order_id, razorpay_signature, amount]):
            flash('Payment or appointment details missing.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Check if doctor exists
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            flash('Selected doctor not found.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Parse date and time
        try:
            appt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            appt_time = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Check if appointment date is in the future
        if appt_date < date.today():
            flash('Appointment date must be in the future.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Check if appointment already exists for the same doctor, date, and time
        existing_appointment = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='scheduled'
        ).first()

        if existing_appointment:
            flash('This time slot is already booked. Please choose a different time.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Verify Razorpay payment
        from app.payment.razorpay_utils import verify_payment
        payment_verified = verify_payment(razorpay_payment_id, razorpay_order_id, razorpay_signature)
        if not payment_verified:
            flash('Payment verification failed. Please try again.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        # Create new appointment
        new_appointment = Appointment(
            patient_id=session['user_id'],
            doctor_id=doctor_id,
            patient_name=session['user_name'],
            appointment_date=appt_date,
            appointment_time=appt_time,
            reason=reason,
            status='scheduled'
        )
        db.session.add(new_appointment)
        db.session.commit()

        # Store payment record
        from app.models import Payment
        payment = Payment(
            appointment_id=new_appointment.id,
            razorpay_payment_id=razorpay_payment_id,
            amount=float(amount),
            currency='INR',
            status='success',
        )
        db.session.add(payment)
        db.session.commit()

        flash('Appointment booked and payment successful!', 'success')
        return redirect(url_for('patient.my_appointments'))

    except Exception as e:
        db.session.rollback()
        flash('An error occurred while booking the appointment. Please try again.', 'danger')
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
