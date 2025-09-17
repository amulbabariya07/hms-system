from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User
from . import admin_bp, clean_mobile_number

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
