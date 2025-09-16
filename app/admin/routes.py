from app.models import Payment, Appointment, Doctor, Specialization
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Payment, Appointment, Doctor, User, MailSetting, Specialization
from werkzeug.security import generate_password_hash
from datetime import datetime
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


@admin_bp.route('/configuration/receptionist-auth', methods=['POST'])
def update_receptionist_auth():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        
        # Validation
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'})
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters long'})
        
        if len(password) < 3:
            return jsonify({'success': False, 'message': 'Password must be at least 3 characters long'})
        
        session['receptionist_credentials'] = {
            'username': username,
            'password': password
        }
        
        if 'receptionist_logged_in' in session:
            session.pop('receptionist_logged_in', None)
            session.pop('receptionist_username', None)
        
        return jsonify({'success': True, 'message': 'Receptionist credentials updated successfully! The receptionist will need to log in again with the new credentials.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error updating credentials'})

@admin_bp.route('/doctors')
def admin_doctors():
    if 'admin_logged_in' not in session:
        flash('Please login to access doctors.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    doctors = Doctor.query.all()
    specializations = Specialization.query.all()  # <-- make sure this is here
    return render_template(
        'admin/doctors.html',
        doctors=doctors,
        specializations=specializations  # <-- pass to template
    )

@admin_bp.route('/doctors/add', methods=['POST'])
def admin_add_doctor():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        full_name = request.form.get('full_name')
        mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
        email = request.form.get('email', '')
        specialization_id = request.form.get('specialization_id')  # <-- updated
        license_number = request.form.get('license_number')
        experience_years = request.form.get('experience_years')
        qualification = request.form.get('qualification')
        hospital_affiliation = request.form.get('hospital_affiliation', '')
        password = request.form.get('password')
        appointments_per_day = request.form.get('appointments_per_day', 10)  # <-- added

        # Validation
        if not all([full_name, mobile_number, specialization_id, license_number, 
                    experience_years, qualification, password, appointments_per_day]):
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
            appointments_per_day = int(appointments_per_day)
            if experience_years < 0 or experience_years > 50:
                return jsonify({'success': False, 'message': 'Experience years must be between 0 and 50.'})
            if appointments_per_day < 1 or appointments_per_day > 50:
                return jsonify({'success': False, 'message': 'Appointments per day must be between 1 and 50.'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Experience and appointments must be valid numbers.'})

        hashed_password = generate_password_hash(password)
        new_doctor = Doctor(
            full_name=full_name,
            mobile_number=mobile_number,
            email=email if email else None,
            specialization_id=specialization_id,  # store ID, not name
            license_number=license_number,
            experience_years=experience_years,
            qualification=qualification,
            hospital_affiliation=hospital_affiliation if hospital_affiliation else None,
            password=hashed_password,
            is_verified=True,
            appointments_per_day=appointments_per_day
        )

        db.session.add(new_doctor)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Doctor added successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while adding the doctor.'})


@admin_bp.route('/doctors/edit/<int:doctor_id>', methods=['POST'])
def admin_edit_doctor(doctor_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        doctor = Doctor.query.get_or_404(doctor_id)
        
        full_name = request.form.get('full_name')
        mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
        email = request.form.get('email', '')
        specialization = request.form.get('specialization')
        license_number = request.form.get('license_number')
        experience_years = request.form.get('experience_years')
        qualification = request.form.get('qualification')
        hospital_affiliation = request.form.get('hospital_affiliation', '')
        appointments_per_day = request.form.get('appointments_per_day', doctor.appointments_per_day)

        # Validation
        if not all([full_name, mobile_number, specialization, license_number, 
                    experience_years, qualification]):
            return jsonify({'success': False, 'message': 'All required fields must be filled.'})

        # Check if mobile number or license number already exists (excluding current doctor)
        existing_doctor = Doctor.query.filter(
            ((Doctor.mobile_number == mobile_number) | 
             (Doctor.license_number == license_number)) &
            (Doctor.id != doctor_id)
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

        # Update doctor information
        doctor.full_name = full_name
        doctor.mobile_number = mobile_number
        doctor.email = email if email else None
        doctor.specialization = specialization
        doctor.license_number = license_number
        doctor.experience_years = experience_years
        doctor.qualification = qualification
        doctor.hospital_affiliation = hospital_affiliation if hospital_affiliation else None
        doctor.appointments_per_day = int(appointments_per_day)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Doctor updated successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the doctor.'})

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
    doctor_data = {
        'id': doctor.id,
        'full_name': doctor.full_name,
        'mobile_number': doctor.mobile_number,
        'email': doctor.email,
        'specialization_id': doctor.specialization_id,
        'specialization_name': doctor.specialization.name if doctor.specialization else 'N/A',
        'license_number': doctor.license_number,
        'experience_years': doctor.experience_years,
        'qualification': doctor.qualification,
        'appointments_per_day': doctor.appointments_per_day,
        'hospital_affiliation': doctor.hospital_affiliation,
        'is_verified': doctor.is_verified,
        'created_at': doctor.created_at.isoformat()
        }
    return jsonify({'success': True, 'doctor': doctor_data})


@admin_bp.route('/patients')
def admin_patients():
    if 'admin_logged_in' not in session:
        flash('Please login to access patients.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    patients = User.query.all()
    return render_template('admin/patients.html', patients=patients)

@admin_bp.route('/patients/edit/<int:patient_id>', methods=['POST'])
def admin_edit_patient(patient_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        patient = User.query.get_or_404(patient_id)
        
        full_name = request.form.get('full_name')
        mobile_number = clean_mobile_number(request.form.get('mobile_number', ''))
        email = request.form.get('email', '')
        age = request.form.get('age')
        gender = request.form.get('gender')

        # Validation
        if not all([full_name, mobile_number, age, gender]):
            return jsonify({'success': False, 'message': 'All required fields must be filled.'})

        # Check if mobile number already exists (excluding current patient)
        existing_patient = User.query.filter(
            (User.mobile_number == mobile_number) & (User.id != patient_id)
        ).first()
        
        if existing_patient:
            return jsonify({'success': False, 'message': 'Mobile number already registered.'})

        try:
            age = int(age)
            if age < 0 or age > 150:
                return jsonify({'success': False, 'message': 'Age must be between 0 and 150.'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Age must be a valid number.'})

        # Update patient information
        patient.full_name = full_name
        patient.mobile_number = mobile_number
        patient.email = email if email else None
        patient.age = age
        patient.gender = gender

        db.session.commit()
        return jsonify({'success': True, 'message': 'Patient updated successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the patient.'})

@admin_bp.route('/patients/details/<int:patient_id>')
def admin_patient_details(patient_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

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

@admin_bp.route('/appointments')
def admin_appointments():
    if 'admin_logged_in' not in session:
        flash('Please login to access appointments.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return render_template('admin/appointments.html', appointments=appointments)

@admin_bp.route('/appointments/update-status/<int:appointment_id>', methods=['POST'])
def admin_update_appointment_status(appointment_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
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

@admin_bp.route('/appointments/details/<int:appointment_id>')
def admin_appointment_details(appointment_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    edit_mode = request.args.get('edit', 'false').lower() == 'true'
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        # Render the wizard template with appointment and edit flag
        return render_template(
            'wizard/appointment_details.html',
            appointment=appointment,
            edit=edit_mode
        )
    except Exception as e:
        return render_template('wizard/appointment_details.html', appointment=None, edit=edit_mode)

@admin_bp.route('/appointments/edit/<int:appointment_id>', methods=['POST'])
def admin_edit_appointment(appointment_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        symptoms = request.form.get('symptoms')
        status = request.form.get('status')

        # Validation
        if not all([appointment_date, appointment_time, symptoms, status]):
            return jsonify({'success': False, 'message': 'All fields must be filled.'})

        if status not in ['scheduled', 'completed', 'cancelled']:
            return jsonify({'success': False, 'message': 'Invalid status'})

        try:
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date or time format'})

        # Update appointment information
        appointment.appointment_date = appointment_date
        appointment.appointment_time = appointment_time
        appointment.symptoms = symptoms
        appointment.status = status

        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment updated successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the appointment.'})

@admin_bp.route('/email-configuration', methods=['GET', 'POST'])
def email_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access Email Configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))

    mail_setting = MailSetting.query.first()
    if request.method == 'POST':
        mail_server = request.form.get('mail_server')
        mail_port = request.form.get('mail_port', type=int)
        mail_use_tls = request.form.get('mail_use_tls') == 'True'
        mail_username = request.form.get('mail_username')
        mail_password = request.form.get('mail_password')
        mail_default_name = request.form.get('mail_default_name')
        mail_default_email = request.form.get('mail_default_email')

        if mail_setting:
            mail_setting.mail_server = mail_server
            mail_setting.mail_port = mail_port
            mail_setting.mail_use_tls = mail_use_tls
            mail_setting.mail_username = mail_username
            mail_setting.mail_password = mail_password
            mail_setting.mail_default_name = mail_default_name
            mail_setting.mail_default_email = mail_default_email
        else:
            mail_setting = MailSetting(
                mail_server=mail_server,
                mail_port=mail_port,
                mail_use_tls=mail_use_tls,
                mail_username=mail_username,
                mail_password=mail_password,
                mail_default_name=mail_default_name,
                mail_default_email=mail_default_email
            )
            db.session.add(mail_setting)
        db.session.commit()
        flash('Email configuration updated successfully.', 'success')
        return redirect(url_for('admin.email_configuration'))

    return render_template('admin/email_configuration.html', mail_setting=mail_setting)


# Payment Records view
@admin_bp.route('/payment-records', methods=['GET'])
def admin_payment_records():
    search = request.args.get('search', '').strip()
    query = Payment.query.join(Appointment)
    if search:
        query = query.filter(Appointment.patient_name.ilike(f'%{search}%'))
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payment_records.html', payments=payments)


@admin_bp.route("/appointment/details")
def appointment_details():
    appointment_id = request.args.get("id")
    mode = request.args.get("mode", "view")  # "view" or "edit"
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template("wizard/appointment_details.html", appointment=appointment, mode=mode)

@admin_bp.route('/specializations')
def admin_specializations():
    if 'admin_logged_in' not in session:
        flash('Please login to access specializations.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    specializations = Specialization.query.order_by(Specialization.created_at.desc()).all()
    return render_template('admin/specializations.html', specializations=specializations)


@admin_bp.route('/specializations/add', methods=['POST'])
def admin_add_specialization():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Name is required.'})

        # Prevent duplicates
        if Specialization.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Specialization already exists.'})

        specialization = Specialization(name=name, description=description)
        db.session.add(specialization)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Specialization added successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while adding specialization.'})


@admin_bp.route('/specializations/edit/<int:spec_id>', methods=['POST'])
def admin_edit_specialization(spec_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        specialization = Specialization.query.get_or_404(spec_id)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Name is required.'})

        # Check duplicate (exclude current)
        existing = Specialization.query.filter(Specialization.name == name, Specialization.id != spec_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Specialization name already exists.'})

        specialization.name = name
        specialization.description = description
        db.session.commit()
        return jsonify({'success': True, 'message': 'Specialization updated successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while updating specialization.'})


@admin_bp.route('/specializations/delete/<int:spec_id>', methods=['POST'])
def admin_delete_specialization(spec_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        specialization = Specialization.query.get_or_404(spec_id)
        db.session.delete(specialization)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Specialization deleted successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while deleting specialization.'})

@admin_bp.route('/doctors/add', methods=['GET'])
def admin_add_doctor_form():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    specializations = Specialization.query.order_by(Specialization.name.asc()).all()
    return render_template('admin/add_doctor.html', specializations=specializations)