from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Doctor, Appointment, User, Specialization
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import re

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

doctor_bp = Blueprint('doctor', __name__, template_folder='templates')

@doctor_bp.route('/prescription/<int:prescription_id>/view', methods=['GET'])
def view_prescription_readonly(prescription_id):
    from app.models import MedicalPrescription, Medicine, Doctor
    pres = MedicalPrescription.query.get_or_404(prescription_id)
    doctor_id = session.get('doctor_id')
    if not doctor_id or (pres.doctor_id != doctor_id and pres.appointment.doctor_id != doctor_id):
        return "Unauthorized", 403
    medicines = pres.medicines
    doctor = pres.doctor
    appointment = pres.appointment
    return render_template('doctor/prescription_readonly.html', prescription=pres, medicines=medicines, doctor=doctor, appointment=appointment)

@doctor_bp.route('/patient/<int:patient_id>/timeline')
def patient_timeline(patient_id):
    from app.models import Appointment
    appointments = (
        Appointment.query
        .filter_by(patient_id=patient_id)
        .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        .all()
    )
    return render_template(
        'doctor/patient_timeline.html',
        appointments=appointments
    )

@doctor_bp.route('/login')
def doctor_login():
    if 'doctor_logged_in' in session:
        return redirect(url_for('doctor.doctor_dashboard'))
    specializations = Specialization.query.order_by(Specialization.name).all()
    return render_template('doctor/auth.html', specializations=specializations, doctor=None)


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
    specialization_id = request.form.get('specialization_id')
    license_number = request.form.get('license_number')
    experience_years = request.form.get('experience_years')
    qualification = request.form.get('qualification')
    hospital_affiliation = request.form.get('hospital_affiliation', '')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not specialization_id:
        flash('Please select a specialization.', 'danger')
        specializations = Specialization.query.order_by(Specialization.name).all()
        return render_template('doctor/auth.html', specializations=specializations)

    # Validation
    if not all([full_name, mobile_number, specialization_id, license_number, email, password]):
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
        specialization_id=specialization_id,
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
    view_type = request.args.get('view', 'kanban')  # default to kanban, can be 'list' or 'kanban'
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

    # Compute display status for each appointment using model helper
    for appt in appointments:
        appt.display_status = appt.get_display_status()

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
        valid_transitions = {
            'scheduled': ['confirmed', 'cancelled'],
            'confirmed': ['under_consultation', 'cancelled'],
            'under_consultation': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': [],
        }
        # Allow 'scheduled' to 'today_scheduled' as a display state, not a DB state
        if appointment.status not in valid_transitions or new_status not in valid_transitions[appointment.status]:
            return jsonify({'success': False, 'message': 'Invalid status transition'})
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
        return redirect(url_for('doctor.doctor_login'))

    doctor = Doctor.query.get(session['doctor_logged_in'])
    specializations = Specialization.query.order_by(Specialization.name).all()
    return render_template('doctor/profile.html', doctor=doctor, specializations=specializations)


@doctor_bp.route('/logout')
def doctor_logout():
    session.pop('doctor_logged_in', None)
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('doctor.doctor_login'))

@doctor_bp.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'doctor_logged_in' not in session:
        return redirect(url_for('doctor.doctor_login'))

    doctor = Doctor.query.get(session['doctor_logged_in'])
    specializations = Specialization.query.order_by(Specialization.name).all()

    doctor.full_name = request.form.get('full_name')
    doctor.email = request.form.get('email')
    doctor.hospital_affiliation = request.form.get('hospital_affiliation')
    doctor.experience_years = request.form.get('experience_years')
    doctor.qualification = request.form.get('qualification')
    doctor.specialization_id = request.form.get('specialization_id')

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
    from flask import request, redirect, url_for, flash, session
    from app.models import MedicalPrescription, Appointment, Doctor
    if 'doctor_id' not in session:
        flash('Please login as doctor.', 'danger')
        return redirect(url_for('doctor.doctor_login'))
    import json
    appointment_id = request.form.get('appointment_id')
    instructions = request.form.get('instructions')
    doctor_id = session['doctor_id']
    # Expect medicines as JSON string from frontend
    medicines_json = request.form.get('medicines_json')
    if not appointment_id or not medicines_json:
        flash('All fields are required.', 'danger')
        return redirect(url_for('doctor.doctor_appointments'))
    try:
        medicines = json.loads(medicines_json)
        if not isinstance(medicines, list) or not medicines:
            raise ValueError
    except Exception:
        flash('Invalid medicines data.', 'danger')
        return redirect(url_for('doctor.doctor_appointments'))
    from app import db
    prescription = MedicalPrescription(
        appointment_id=appointment_id,
        doctor_id=doctor_id,
        instructions=instructions
    )
    db.session.add(prescription)
    db.session.commit()

    # Add each medicine as a Medicine object
    from app.models import Medicine
    for med in medicines:
        medicine = Medicine(
            prescription_id=prescription.id,
            name=med.get('name'),
            type=med.get('type'),
            dosage=med.get('dosage'),
            frequency=med.get('frequency'),
            days=med.get('days'),
            timing=med.get('timing'),
            quantity=med.get('quantity'),
            notes=med.get('notes')
        )
        db.session.add(medicine)
    db.session.commit()
    flash('Prescription added successfully!', 'success')
    return redirect(url_for('doctor.doctor_appointments'))

@doctor_bp.route('/appointment/<int:appointment_id>/prescription-info')
def get_prescription_info(appointment_id):
    if 'doctor_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    from app.models import MedicalPrescription
    prescription = MedicalPrescription.query.filter_by(appointment_id=appointment_id).first()
    
    return jsonify({
        'has_prescription': prescription is not None,
        'prescription_id': prescription.id if prescription else None
    })