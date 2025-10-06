# Medicine model for individual medicine entries in a prescription

# ContactQuery model for Contact Us form
from datetime import datetime
from app import db

class Medicine(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('medical_prescriptions.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # tablet, liquid, injection
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # morning, afternoon, night
    days = db.Column(db.Integer, nullable=False)
    timing = db.Column(db.String(20), nullable=False)  # before, after food
    quantity = db.Column(db.String(50), nullable=True)  # e.g. 5ml, 1 vial
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    def __repr__(self):
        return f'<Medicine {self.name}>'

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
    specialization_id = db.Column(db.Integer, db.ForeignKey('specializations.id'), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    experience_years = db.Column(db.Integer, nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    hospital_affiliation = db.Column(db.String(200), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    appointments_per_day = db.Column(db.Integer, nullable=True, default=10)
    
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
    appointment_time = db.Column(db.Time)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, today_scheduled, confirmed, under_consultation, completed, cancelled
    def get_display_status(self):
        today = datetime.utcnow().date()
        if self.status == 'scheduled' and self.appointment_date == today:
            return 'Today Scheduled'
        elif self.status == 'scheduled':
            return 'Scheduled'
        elif self.status == 'confirmed':
            return 'Confirmed'
        elif self.status == 'under_consultation':
            return 'Under Consultation'
        elif self.status == 'completed':
            return 'Completed'
        elif self.status == 'cancelled':
            return 'Cancelled'
        else:
            return self.status.title()
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
    medicines = db.relationship('Medicine', backref='prescription', lazy=True)
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

    # Patient Intake Form Model
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from . import db  # Assuming db is SQLAlchemy instance from Flask

class PatientIntakeForm(db.Model):
    __tablename__ = 'patient_intake_form'

    # 1. Personal Information
    id = Column(Integer, primary_key=True)  # Patient_ID
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    age = Column(Integer)
    gender = Column(String(20))
    blood_group = Column(String(10))
    national_id = Column(String(50))  # National_ID / Passport / SSN
    marital_status = Column(String(20))  # Single, Married, Divorced, Widowed
    occupation = Column(String(100))
    education_level = Column(String(100))
    language_preference = Column(String(50))

    # 2. Contact Details
    phone_number = Column(String(20))
    alternate_phone = Column(String(20))
    email_address = Column(String(100))
    permanent_address = Column(Text)
    current_address = Column(Text)
    emergency_contact_name = Column(String(100))
    emergency_contact_relationship = Column(String(50))
    emergency_contact_phone = Column(String(20))

    # 3. Insurance Information
    insurance_provider = Column(String(100))
    insurance_policy_number = Column(String(50))
    coverage_details = Column(Text)
    validity_period = Column(String(50))
    primary_policy_holder = Column(String(100))

    # 4. Medical History
    allergies = Column(Text)  # Drug, Food, Environmental
    past_illnesses = Column(Text)  # Diabetes, Hypertension, Asthma, etc.
    past_surgeries = Column(Text)
    current_medications = Column(Text)
    family_history = Column(Text)  # Heart disease, Cancer, etc.
    vaccination_status = Column(Text)
    chronic_conditions = Column(Text)

    # 5. Lifestyle & Social History
    smoking_status = Column(String(50))  # Yes/No, Frequency
    alcohol_use = Column(String(50))  # Yes/No, Frequency
    drug_use = Column(String(100))  # Yes/No, Type
    exercise_habits = Column(Text)
    diet_pattern = Column(String(50))  # Vegetarian, Non-Vegetarian, Vegan, etc.
    sleep_pattern = Column(String(100))
    stress_level = Column(String(50))

    # 6. Reproductive / OB-GYN History (if applicable)
    menstrual_cycle = Column(String(20))  # Regular/Irregular
    last_menstrual_period = Column(Date)
    pregnancy_status = Column(String(50))
    number_of_pregnancies = Column(Integer)
    number_of_children = Column(Integer)
    contraceptive_use = Column(String(100))

    # 7. Visit / Clinical Data
    reason_for_visit = Column(Text)
    symptoms = Column(Text)
    diagnosis = Column(Text)
    treatment_plan = Column(Text)
    doctor_assigned = Column(String(100))
    visit_date = Column(Date)
    next_appointment_date = Column(Date)

    # 8. Consent & Legal
    consent_form_signed = Column(Boolean, default=False)
    consent_date = Column(Date)
    legal_guardian_name = Column(String(100))
    guardian_relationship = Column(String(50))
    guardian_signature = Column(String(200))

    # 9. Administrative
    registration_date = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))  # Staff/Doctor ID
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default='Active')  # Active, Inactive, Archived

    def __repr__(self):
        return f"<PatientIntakeForm {self.first_name} {self.last_name}>"

# Payment model for Razorpay integration
class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship('Appointment', backref='payments')

    def __repr__(self):
        return f'<Payment {self.razorpay_payment_id}>'


class Specialization(db.Model):
    __tablename__ = 'specializations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with doctors (One specialization -> many doctors)
    doctors = db.relationship('Doctor', backref='specialization', lazy=True)

    def __repr__(self):
        return f'<Specialization {self.name}>'
