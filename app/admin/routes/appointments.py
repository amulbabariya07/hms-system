from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Appointment, PatientIntakeForm, MedicalPrescription
from datetime import datetime
from . import admin_bp

@admin_bp.route('/appointments')
def admin_appointments():
    if 'admin_logged_in' not in session:
        flash('Please login to access appointments.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    # Compute display status for each appointment
    today = datetime.now().date()
    for appt in appointments:
        if appt.status == 'cancelled':
            appt.display_status = 'Cancelled'
        elif appt.status == 'completed':
            appt.display_status = 'Appointment Done'
        elif appt.appointment_date == today:
            appt.display_status = 'Today Scheduled'
        elif appt.status == 'scheduled':
            appt.display_status = 'Appointment Booked'
        else:
            appt.display_status = appt.status.title()
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

@admin_bp.route("/appointment/details")
def appointment_details():
    appointment_id = request.args.get("id")
    mode = request.args.get("mode", "view")  # "view" or "edit"
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template("wizard/appointment_details.html", appointment=appointment, mode=mode)

@admin_bp.route('/patient/<int:patient_id>/intake-readonly')
def admin_patient_intake_readonly(patient_id):
    """Show readonly intake form for patient (admin)"""
    intake_form = PatientIntakeForm.query.filter_by(patient_id=patient_id).first()
    if not intake_form:
        return '', 204
    return render_template('doctor/patient_intake_readonly.html', intake_form=intake_form)

@admin_bp.route('/patient/<int:patient_id>/timeline')
def admin_patient_timeline(patient_id):
    """Show patient timeline (admin)"""
    # Copy doctor logic for timeline
    from app.models import Appointment, MedicalPrescription
    appointments = Appointment.query.filter_by(user_id=patient_id).order_by(Appointment.appointment_date.desc()).all()
    prescriptions = MedicalPrescription.query.filter_by(patient_id=patient_id).order_by(MedicalPrescription.created_at.desc()).all()
    timeline_data = {
        'appointments': appointments,
        'prescriptions': prescriptions
    }
    return render_template('doctor/patient_timeline.html', timeline=timeline_data)

@admin_bp.route('/appointment/<int:appointment_id>/prescription-info')
def admin_prescription_info(appointment_id):
    """Return prescription info for appointment (admin)"""
    prescription = MedicalPrescription.query.filter_by(appointment_id=appointment_id).first()
    if prescription:
        return jsonify({'has_prescription': True, 'prescription_id': prescription.id})
    return jsonify({'has_prescription': False})

@admin_bp.route('/prescription/<int:prescription_id>/view')
def admin_view_prescription(prescription_id):
    """Show readonly prescription for admin"""
    prescription = MedicalPrescription.query.get_or_404(prescription_id)
    return render_template('doctor/prescription_readonly.html', prescription=prescription)
