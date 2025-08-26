from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Doctor, Appointment, User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import re

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

doctor_bp = Blueprint('doctor', __name__, template_folder='templates')

@doctor_bp.route('/login')
def doctor_login():
    if 'doctor_logged_in' in session:
        return redirect(url_for('doctor.doctor_dashboard'))
    return render_template('doctor/auth.html')

@doctor_bp.route('/login', methods=['POST'])
def doctor_login_post():
    if request.form.get('form_type') != 'login':
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('doctor.doctor_login'))

    mobile_number = clean_mobile_number(request.form['mobile_number'])
    password = request.form['password']

    doctor = Doctor.query.filter_by(mobile_number=mobile_number).first()

    if doctor and check_password_hash(doctor.password, password):
        # Check if doctor is verified
        if not doctor.is_verified:
            flash('Your account is pending approval. Please wait for admin approval before logging in.', 'warning')
            return render_template('doctor/auth.html')
        
        session['doctor_logged_in'] = True
        session['doctor_id'] = doctor.id
        session['doctor_name'] = doctor.full_name
        flash(f'Welcome back, Dr. {doctor.full_name}!', 'success')
        return redirect(url_for('doctor.doctor_dashboard'))
    else:
        flash('Invalid mobile number or password', 'danger')
        return render_template('doctor/auth.html')

@doctor_bp.route('/signup', methods=['POST'])
def doctor_signup():
    if request.form.get('form_type') != 'signup':
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('doctor.doctor_login'))

    full_name = request.form.get('full_name')
    mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
    email = request.form.get('email', '')
    specialization = request.form.get('specialization')
    license_number = request.form.get('license_number')
    experience_years = request.form.get('experience_years')
    qualification = request.form.get('qualification')
    hospital_affiliation = request.form.get('hospital_affiliation', '')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Validation
    if not all([full_name, mobile_number, specialization, license_number, 
                experience_years, qualification, password, confirm_password]):
        flash('All required fields must be filled.', 'danger')
        return render_template('doctor/auth.html')

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('doctor/auth.html')

    # Check if mobile number or license number already exists
    existing_doctor = Doctor.query.filter(
        (Doctor.mobile_number == mobile_number) | 
        (Doctor.license_number == license_number)
    ).first()
    
    if existing_doctor:
        if existing_doctor.mobile_number == mobile_number:
            flash('Mobile number already registered.', 'danger')
        else:
            flash('License number already registered.', 'danger')
        return render_template('doctor/auth.html')

    try:
        experience_years = int(experience_years)
        if experience_years < 0 or experience_years > 50:
            flash('Experience years must be between 0 and 50.', 'danger')
            return render_template('doctor/auth.html')
    except ValueError:
        flash('Experience years must be a valid number.', 'danger')
        return render_template('doctor/auth.html')

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
        is_verified=False  # Set to False by default, requires admin approval
    )

    db.session.add(new_doctor)
    db.session.commit()

    flash('Doctor account created successfully! Your account is pending admin approval. You will be able to login once approved.', 'success')
    return render_template('doctor/auth.html')

@doctor_bp.route('/dashboard')
def doctor_dashboard():
    if 'doctor_logged_in' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('doctor.doctor_login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    return render_template('doctor/dashboard.html', doctor=doctor)

@doctor_bp.route('/appointments')
def doctor_appointments():
    if 'doctor_logged_in' not in session:
        flash('Please login to access appointments.', 'warning')
        return redirect(url_for('doctor.doctor_login'))
    
    doctor_id = session['doctor_id']
    view_type = request.args.get('view', 'list')  # list or kanban
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    search_query = request.args.get('search', '')
    
    try:
        # Parse the selected date
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        filter_date = date.today()
        selected_date = filter_date.strftime('%Y-%m-%d')
    
    # Base query for doctor's appointments
    appointments_query = Appointment.query.filter_by(doctor_id=doctor_id)
    
    # Filter by date
    appointments_query = appointments_query.filter(Appointment.appointment_date == filter_date)
    
    # Apply search filter if provided
    if search_query:
        appointments_query = appointments_query.join(User).filter(
            User.full_name.ilike(f'%{search_query}%')
        )
    
    appointments = appointments_query.order_by(Appointment.appointment_time).all()
    
    # Get statistics
    today = date.today()
    today_appointments = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=today).count()
    total_appointments = Appointment.query.filter_by(doctor_id=doctor_id).count()
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='completed').count()
    
    stats = {
        'today': today_appointments,
        'total': total_appointments,
        'completed': completed_appointments,
        'pending': total_appointments - completed_appointments
    }
    
    return render_template('doctor/appointments.html', 
                         appointments=appointments,
                         stats=stats,
                         view_type=view_type,
                         selected_date=selected_date,
                         search_query=search_query,
                         filter_date=filter_date,
                         datetime=datetime,
                         date=date)

@doctor_bp.route('/appointments/update-status/<int:appointment_id>', methods=['POST'])
def doctor_update_appointment_status(appointment_id):
    if 'doctor_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id, 
            doctor_id=session['doctor_id']
        ).first_or_404()
        
        new_status = request.json.get('status')
        
        if new_status not in ['scheduled', 'completed', 'cancelled']:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        appointment.status = new_status
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Appointment status updated to {new_status}'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the appointment.'})

@doctor_bp.route('/appointments/details/<int:appointment_id>')
def doctor_appointment_details(appointment_id):
    if 'doctor_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id, 
            doctor_id=session['doctor_id']
        ).first_or_404()
        
        return jsonify({
            'success': True,
            'appointment': {
                'id': appointment.id,
                'patient_name': appointment.user.full_name if appointment.user else 'N/A',
                'patient_mobile': appointment.user.mobile_number if appointment.user else 'N/A',
                'patient_age': appointment.user.age if appointment.user else 'N/A',
                'patient_gender': appointment.user.gender if appointment.user else 'N/A',
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else 'N/A',
                'appointment_time': appointment.appointment_time.strftime('%H:%M') if appointment.appointment_time else 'N/A',
                'symptoms': appointment.symptoms if hasattr(appointment, 'symptoms') else 'N/A',
                'status': appointment.status,
                'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching appointment details'})

@doctor_bp.route('/profile')
def doctor_profile():
    if 'doctor_logged_in' not in session:
        flash('Please login to access your profile.', 'warning')
        return redirect(url_for('doctor.doctor_login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    return render_template('doctor/profile.html', doctor=doctor)

@doctor_bp.route('/logout')
def doctor_logout():
    session.pop('doctor_logged_in', None)
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('doctor.doctor_login'))

@doctor_bp.route('/edit-profile', methods=['POST'])
def doctor_edit_profile():
    if 'doctor_logged_in' not in session:
        flash('Please login to edit your profile.', 'warning')
        return redirect(url_for('doctor.doctor_login'))

    doctor = Doctor.query.get(session['doctor_id'])
    doctor.full_name = request.form.get('full_name')
    doctor.mobile_number = request.form.get('mobile_number')
    doctor.email = request.form.get('email')
    doctor.specialization = request.form.get('specialization')
    doctor.license_number = request.form.get('license_number')
    doctor.experience_years = request.form.get('experience_years')
    doctor.qualification = request.form.get('qualification')
    doctor.hospital_affiliation = request.form.get('hospital_affiliation')
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('doctor.doctor_profile'))


@doctor_bp.route('/change-password', methods=['GET', 'POST'])
def doctor_change_password():
    if 'doctor_logged_in' not in session:
        flash('Please login to change your password.', 'warning')
        return redirect(url_for('doctor.doctor_login'))

    if request.method == 'GET':
        return render_template('doctor/change_password.html')

    doctor = Doctor.query.get(session['doctor_id'])
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not check_password_hash(doctor.password, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('doctor.doctor_change_password'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('doctor.doctor_change_password'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'danger')
        return redirect(url_for('doctor.doctor_change_password'))

    doctor.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('doctor.doctor_profile'))

@doctor_bp.route('/patients')
def patients():
    if 'doctor_logged_in' not in session:
        flash('Please login to view your patients.', 'warning')
        return redirect(url_for('doctor.doctor_login'))

    doctor = Doctor.query.get(session['doctor_id'])
    # Assuming User model has doctor_id or appointments are linked to doctor
    patients = User.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct().all()
    return render_template('doctor/patients.html', patients=patients)

@doctor_bp.route('/add-prescription', methods=['POST'])
def add_prescription():
    # Your logic for adding prescription
    return "Prescription added"