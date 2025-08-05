from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import PatientAppointment
from datetime import datetime

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
