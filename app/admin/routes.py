from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Doctor
from werkzeug.security import generate_password_hash
import re

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Temporary fake "DB"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
CURRENT_EMAIL = "httpsbabariya121@gmail.com"

admin_store = {
    "username": "admin",
    "password": "admin",  # use hash in production
}

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

@admin_bp.route('/login')
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/login.html')

@admin_bp.route('/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        session['admin_username'] = ADMIN_USERNAME
        flash('Login successful.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        flash('Invalid credentials.', 'danger')
        return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Logged out.', 'info')
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash('Please login to access dashboard.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    from app.models import User, Appointment
    from datetime import date
    
    # Get statistics
    today = date.today()
    today_appointments = Appointment.query.filter(Appointment.appointment_date == today).count()
    total_appointments = Appointment.query.count()
    total_doctors = Doctor.query.filter_by(is_verified=True).count()
    pending_doctors = Doctor.query.filter_by(is_verified=False).count()
    total_patients = User.query.count()
    
    stats = {
        'today_appointments': today_appointments,
        'total_appointments': total_appointments,
        'total_doctors': total_doctors,
        'pending_doctors': pending_doctors,
        'total_patients': total_patients
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/configuration')
def admin_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))
    return render_template('admin/configuration.html')

@admin_bp.route('/doctors')
def admin_doctors():
    if 'admin_logged_in' not in session:
        flash('Please login to access doctors.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    doctors = Doctor.query.all()
    return render_template('admin/doctors.html', doctors=doctors)

@admin_bp.route('/doctors/add', methods=['POST'])
def admin_add_doctor():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        full_name = request.form.get('full_name')
        mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
        email = request.form.get('email', '')
        specialization = request.form.get('specialization')
        license_number = request.form.get('license_number')
        experience_years = request.form.get('experience_years')
        qualification = request.form.get('qualification')
        hospital_affiliation = request.form.get('hospital_affiliation', '')
        password = request.form.get('password')

        # Validation
        if not all([full_name, mobile_number, specialization, license_number, 
                    experience_years, qualification, password]):
            return jsonify({'success': False, 'message': 'All required fields must be filled.'})

        # Check if mobile number or license number already exists
        existing_doctor = Doctor.query.filter(
            (Doctor.mobile_number == mobile_number) | 
            (Doctor.license_number == license_number)
        ).first()
        
        if existing_doctor:
            if existing_doctor.mobile_number == mobile_number:
                return jsonify({'success': False, 'message': 'Mobile number already registered.'})
            else:
                return jsonify({'success': False, 'message': 'License number already registered.'})

        try:
            experience_years = int(experience_years)
            if experience_years < 0 or experience_years > 50:
                return jsonify({'success': False, 'message': 'Experience years must be between 0 and 50.'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Experience years must be a valid number.'})

        hashed_password = generate_password_hash(password)
        new_doctor = Doctor(
            full_name=full_name,
            mobile_number=mobile_number,
            email=email if email else None,
            specialization=specialization,
            license_number=license_number,
            experience_years=experience_years,
            qualification=qualification,
            hospital_affiliation=hospital_affiliation if hospital_affiliation else None,
            password=hashed_password,
            is_verified=True  # Admin created doctors are auto-approved
        )

        db.session.add(new_doctor)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Doctor added successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while adding the doctor.'})

@admin_bp.route('/doctors/approval')
def admin_doctors_approval():
    if 'admin_logged_in' not in session:
        flash('Please login to access doctors approval.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    pending_doctors = Doctor.query.filter_by(is_verified=False).all()
    return render_template('admin/doctors_approval.html', pending_doctors=pending_doctors)

@admin_bp.route('/doctors/approve/<int:doctor_id>', methods=['POST'])
def admin_approve_doctor(doctor_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        doctor = Doctor.query.get_or_404(doctor_id)
        doctor.is_verified = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Dr. {doctor.full_name} has been approved successfully!'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while approving the doctor.'})

@admin_bp.route('/doctors/reject/<int:doctor_id>', methods=['POST'])
def admin_reject_doctor(doctor_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        doctor = Doctor.query.get_or_404(doctor_id)
        db.session.delete(doctor)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Dr. {doctor.full_name} has been rejected and removed.'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while rejecting the doctor.'})

@admin_bp.route('/doctors/details/<int:doctor_id>')
def admin_doctor_details(doctor_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify({
        'success': True,
        'doctor': {
            'id': doctor.id,
            'full_name': doctor.full_name,
            'mobile_number': doctor.mobile_number,
            'email': doctor.email,
            'specialization': doctor.specialization,
            'license_number': doctor.license_number,
            'experience_years': doctor.experience_years,
            'qualification': doctor.qualification,
            'hospital_affiliation': doctor.hospital_affiliation,
            'created_at': doctor.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_verified': doctor.is_verified
        }
    })

@admin_bp.route('/patients')
def admin_patients():
    if 'admin_logged_in' not in session:
        flash('Please login to access patients.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    from app.models import User
    patients = User.query.all()
    return render_template('admin/patients.html', patients=patients)

@admin_bp.route('/appointments')
def admin_appointments():
    if 'admin_logged_in' not in session:
        flash('Please login to access appointments.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    from app.models import Appointment
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments)

@admin_bp.route('/appointments/update-status/<int:appointment_id>', methods=['POST'])
def admin_update_appointment_status(appointment_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        from app.models import Appointment
        appointment = Appointment.query.get_or_404(appointment_id)
        new_status = request.json.get('status')
        
        if new_status not in ['scheduled', 'completed', 'cancelled']:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        appointment.status = new_status
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Appointment status updated to {new_status}'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the appointment.'})

@admin_bp.route('/patients/details/<int:patient_id>')
def admin_patient_details(patient_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    from app.models import User
    patient = User.query.get_or_404(patient_id)
    return jsonify({
        'success': True,
        'patient': {
            'id': patient.id,
            'full_name': patient.full_name,
            'mobile_number': patient.mobile_number,
            'email': patient.email,
            'age': patient.age,
            'gender': patient.gender,
            'created_at': patient.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'appointment_count': len(patient.appointments) if hasattr(patient, 'appointments') else 0
        }
    })
