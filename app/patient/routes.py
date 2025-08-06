from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import PatientAppointment, User
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

patient_bp = Blueprint('patient', __name__, template_folder='templates')

@patient_bp.route('/')
def patient_home():
    return render_template('patient/home.html')

@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        try:
            # Get form data
            appointment = PatientAppointment(
                patient_name=request.form['patient_name'],
                patient_email=request.form['patient_email'],
                patient_phone=request.form['patient_phone'],
                patient_age=int(request.form['patient_age']),
                patient_gender=request.form['patient_gender'],
                appointment_date=datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date(),
                appointment_time=datetime.strptime(request.form['appointment_time'], '%H:%M').time(),
                department=request.form['department'],
                doctor_preference=request.form.get('doctor_preference', ''),
                symptoms=request.form.get('symptoms', ''),
                emergency=bool(request.form.get('emergency'))
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            flash('Appointment booked successfully! We will contact you soon.', 'success')
            return redirect(url_for('patient.appointment_success'))
            
        except Exception as e:
            flash('Error booking appointment. Please try again.', 'danger')
            return render_template('patient/book_appointment.html')
    
    return render_template('patient/book_appointment.html')

@patient_bp.route('/appointment-success')
def appointment_success():
    return render_template('patient/appointment_success.html')

@patient_bp.route('/appointments')
def view_appointments():
    # For demo purposes, we'll show all appointments
    # In a real app, you'd filter by logged-in user
    appointments = PatientAppointment.query.order_by(PatientAppointment.created_at.desc()).all()
    return render_template('patient/appointments.html', appointments=appointments)

@patient_bp.route('/appointment/<int:appointment_id>')
def appointment_detail(appointment_id):
    appointment = PatientAppointment.query.get_or_404(appointment_id)
    return render_template('patient/appointment_detail.html', appointment=appointment)

@patient_bp.route('/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        mobile_number = request.form['mobile_number']
        password = request.form['password']
        remember_me = bool(request.form.get('remember_me'))
        
        user = User.query.filter_by(mobile_number=mobile_number).first()
        
        if user and check_password_hash(user.password, password):
            # In a real app, you'd use Flask-Login here
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('patient.patient_home'))
        else:
            flash('Invalid mobile number or password', 'danger')
    
    return render_template('patient/auth.html')

@patient_bp.route('/signup', methods=['POST'])
def patient_signup():
    try:
        full_name = request.form['full_name']
        mobile_number = request.form['mobile_number']
        email = request.form.get('email', '')
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('patient/auth.html')
        
        # Check if mobile number already exists
        existing_user = User.query.filter_by(mobile_number=mobile_number).first()
        if existing_user:
            flash('Mobile number already registered', 'danger')
            return render_template('patient/auth.html')
        
        # Create new user
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
        
    except Exception as e:
        flash('Error creating account. Please try again.', 'danger')
        return render_template('patient/auth.html')

@patient_bp.route('/forgot-password')
def forgot_password():
    # This would typically send a reset email
    flash('Password reset feature will be implemented soon! Please contact support.', 'info')
    return redirect(url_for('patient.patient_login'))
