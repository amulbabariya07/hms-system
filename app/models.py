from app import db
from datetime import datetime

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    email = db.Column(db.String(120), unique=True)
    
    # Relationship with appointments
    appointments = db.relationship('PatientAppointment', backref='patient', lazy=True)

class PatientAppointment(db.Model):
    __tablename__ = 'patient_appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(120), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    patient_age = db.Column(db.Integer, nullable=False)
    patient_gender = db.Column(db.String(10), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    doctor_preference = db.Column(db.String(100))
    symptoms = db.Column(db.Text)
    emergency = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to Patient (optional, for registered patients)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
