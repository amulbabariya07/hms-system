from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Doctor, Specialization
from werkzeug.security import generate_password_hash
from . import admin_bp, clean_mobile_number

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
        specialization_id = request.form.get('specialization_id')  # Changed from specialization
        license_number = request.form.get('license_number')
        experience_years = request.form.get('experience_years')
        qualification = request.form.get('qualification')
        hospital_affiliation = request.form.get('hospital_affiliation', '')
        appointments_per_day = request.form.get('appointments_per_day', doctor.appointments_per_day)
        password = request.form.get('password')  # Added password field

        # Validation
        if not all([full_name, mobile_number, specialization_id, license_number, 
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
            appointments_per_day = int(appointments_per_day)
            if experience_years < 0 or experience_years > 50:
                return jsonify({'success': False, 'message': 'Experience years must be between 0 and 50.'})
            if appointments_per_day < 1 or appointments_per_day > 50:
                return jsonify({'success': False, 'message': 'Appointments per day must be between 1 and 50.'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Experience and appointments must be valid numbers.'})

        # Update doctor information
        doctor.full_name = full_name
        doctor.mobile_number = mobile_number
        doctor.email = email if email else None
        doctor.specialization_id = specialization_id  # Changed from specialization
        doctor.license_number = license_number
        doctor.experience_years = experience_years
        doctor.qualification = qualification
        doctor.hospital_affiliation = hospital_affiliation if hospital_affiliation else None
        doctor.appointments_per_day = appointments_per_day

        # Update password if provided
        if password:
            doctor.password = generate_password_hash(password)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Doctor updated successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'An error occurred while updating the doctor: {str(e)}'})

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


@admin_bp.route('/doctors/add', methods=['GET'])
def admin_add_doctor_form():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    specializations = Specialization.query.order_by(Specialization.name.asc()).all()
    return render_template('admin/add_doctor.html', specializations=specializations)
