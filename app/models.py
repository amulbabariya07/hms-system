
# ContactQuery model for Contact Us form
from datetime import datetime
from app import db

class ContactQuery(db.Model):
    __tablename__ = 'contact_queries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    query_type = db.Column(db.String(50), nullable=True, default='general')  # appointment, medical_inquiry, billing, complaint, emergency, general, partnership
    priority = db.Column(db.String(20), nullable=True, default='low')  # low, medium, high
    subject = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='new')  # new, in_progress, resolved, closed
    assigned_to = db.Column(db.String(100), nullable=True)  # staff member handling the query
    response = db.Column(db.Text, nullable=True)  # response from staff
    resolved_at = db.Column(db.DateTime, nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContactQuery {self.name} - {self.query_type}>'

# User model for patient information
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with appointments
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    
    def __repr__(self):
        return f'<User {self.full_name}>'

# Doctor model for doctor information
class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    specialization = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    experience_years = db.Column(db.Integer, nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    hospital_affiliation = db.Column(db.String(200), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Relationship with appointments
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    
    def __repr__(self):
        return f'<Doctor {self.full_name}>'

# Appointment model for managing appointments
class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[patient_id])
    
    def __repr__(self):
        return f'<Appointment {self.patient_name} with Dr. {self.doctor.full_name}>'


# MedicalPrescription model for prescriptions
class MedicalPrescription(db.Model):
    __tablename__ = 'medical_prescriptions'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    medicines = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment = db.relationship('Appointment', backref='prescriptions')
    doctor = db.relationship('Doctor', backref='prescriptions')

    def __repr__(self):
        return f'<MedicalPrescription {self.id}>'


# MailSetting model for SMTP configuration
class MailSetting(db.Model):
    __tablename__ = 'mail_settings'
    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(120), nullable=False)
    mail_port = db.Column(db.Integer, nullable=False)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_username = db.Column(db.String(120), nullable=False)
    mail_password = db.Column(db.String(255), nullable=False)
    mail_default_name = db.Column(db.String(120), nullable=True)
    mail_default_email = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MailSetting {self.mail_server}>'