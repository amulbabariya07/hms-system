from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User, Doctor, Appointment
from datetime import datetime

receptionist_bp = Blueprint('receptionist', __name__, template_folder='templates')

# Receptionist credentials
RECEPTIONIST_USERNAME = "amul"
RECEPTIONIST_PASSWORD = "amul"

def login_required(f):
    """Decorator to require login for receptionist routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'receptionist_logged_in' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('receptionist.receptionist_login'))
        return f(*args, **kwargs)
    return decorated_function

@receptionist_bp.route('/login')
def receptionist_login():
    if 'receptionist_logged_in' in session:
        return redirect(url_for('receptionist.receptionist_dashboard'))
    return render_template('receptionist/login.html')

@receptionist_bp.route('/login', methods=['POST'])
def receptionist_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if username == RECEPTIONIST_USERNAME and password == RECEPTIONIST_PASSWORD:
        session['receptionist_logged_in'] = True
        session['receptionist_username'] = RECEPTIONIST_USERNAME
        flash('Login successful. Welcome to Receptionist Panel!', 'success')
        return redirect(url_for('receptionist.receptionist_dashboard'))
    else:
        flash('Invalid credentials. Please try again.', 'danger')
        return render_template('receptionist/login.html')

@receptionist_bp.route('/logout')
def receptionist_logout():
    session.pop('receptionist_logged_in', None)
    session.pop('receptionist_username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('receptionist.receptionist_login'))

@receptionist_bp.route('/dashboard')
@login_required
def receptionist_dashboard():
    try:
        total_patients = User.query.count() if User else 0
        total_appointments = Appointment.query.count() if Appointment else 0
        today_appointments = Appointment.query.filter(
            Appointment.appointment_date == datetime.now().date()
        ).count() if Appointment else 0
    except:
        total_patients = 0
        total_appointments = 0
        today_appointments = 0
    
    return render_template('receptionist/dashboard.html', 
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         today_appointments=today_appointments)

@receptionist_bp.route('/patients')
@login_required
def receptionist_patients():
    try:
        patients = User.query.all() if User else []
    except:
        patients = []
    return render_template('receptionist/patients.html', patients=patients)

@receptionist_bp.route('/patients/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name')
            mobile_number = request.form.get('mobile_number')
            email = request.form.get('email')
            password = request.form.get('password', 'default123')  # Default password for patients
            
            # Create new patient using User model
            new_patient = User(
                full_name=full_name,
                mobile_number=mobile_number,
                email=email,
                password=password
            )
            
            db.session.add(new_patient)
            db.session.commit()
            
            flash(f'Patient {full_name} has been successfully added!', 'success')
            return redirect(url_for('receptionist.receptionist_patients'))
            
        except Exception as e:
            flash(f'Error adding patient: {str(e)}', 'danger')
            db.session.rollback()
    
    return render_template('receptionist/add_patient.html')

@receptionist_bp.route('/appointments')
@login_required
def receptionist_appointments():
    try:
        appointments = Appointment.query.all() if Appointment else []
    except:
        appointments = []
    return render_template('receptionist/appointments.html', appointments=appointments)

@receptionist_bp.route('/appointments/create', methods=['GET', 'POST'])
@login_required
def create_appointment():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            doctor_id = request.form.get('doctor_id')
            patient_name = request.form.get('patient_name')
            appointment_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
            appointment_time = datetime.strptime(request.form.get('appointment_time'), '%H:%M').time()
            reason = request.form.get('reason')
            
            # Create new appointment
            new_appointment = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                patient_name=patient_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=reason,
                status='scheduled'
            )
            
            db.session.add(new_appointment)
            db.session.commit()
            
            flash('Appointment has been successfully created!', 'success')
            return redirect(url_for('receptionist.receptionist_appointments'))
            
        except Exception as e:
            flash(f'Error creating appointment: {str(e)}', 'danger')
            db.session.rollback()
    
    try:
        patients = User.query.all() if User else []
        doctors = Doctor.query.filter_by(is_verified=True).all() if Doctor else []
    except:
        patients = []
        doctors = []
    
    return render_template('receptionist/create_appointment.html', patients=patients, doctors=doctors)
