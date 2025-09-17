from flask import Blueprint, render_template, session
from app.models import MedicalPrescription, Appointment, Doctor, User
from app import db
from datetime import datetime

patient_medical_bp = Blueprint('patient_medical', __name__, template_folder='templates')

@patient_medical_bp.route('/medical-records')
def medical_records():
    if 'user_id' not in session:
        return render_template('patient/auth.html')
    user_id = session['user_id']
    # Get all prescriptions for this patient, date-wise
    prescriptions = (
        MedicalPrescription.query
        .join(Appointment, MedicalPrescription.appointment_id == Appointment.id)
        .filter(Appointment.patient_id == user_id)
        .order_by(MedicalPrescription.created_at.desc())
        .all()
    )
    return render_template('patient/medical_records.html', prescriptions=prescriptions)
