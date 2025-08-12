from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import Doctor
from werkzeug.security import generate_password_hash, check_password_hash
import re

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

doctor_bp = Blueprint('doctor', __name__, template_folder='templates')

@doctor_bp.route('/login')
def doctor_login():
    if 'doctor_logged_in' in session:
        return redirect(url_for('doctor.doctor_dashboard'))
    return render_template('doctor/auth.html')

@doctor_bp.route('/login', methods=['POST'])
def doctor_login_post():
    if request.form.get('form_type') != 'login':
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('doctor.doctor_login'))

    mobile_number = clean_mobile_number(request.form['mobile_number'])
    password = request.form['password']

    doctor = Doctor.query.filter_by(mobile_number=mobile_number).first()

    if doctor and check_password_hash(doctor.password, password):
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
    specialization = request.form.get('specialization')
    license_number = request.form.get('license_number')
    experience_years = request.form.get('experience_years')
    qualification = request.form.get('qualification')
    hospital_affiliation = request.form.get('hospital_affiliation', '')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Validation
    if not all([full_name, mobile_number, specialization, license_number, 
                experience_years, qualification, password, confirm_password]):
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
        specialization=specialization,
        license_number=license_number,
        experience_years=experience_years,
        qualification=qualification,
        hospital_affiliation=hospital_affiliation if hospital_affiliation else None,
        password=hashed_password
    )

    db.session.add(new_doctor)
    db.session.commit()

    flash('Doctor account created successfully! Please login.', 'success')
    return render_template('doctor/auth.html')

@doctor_bp.route('/dashboard')
def doctor_dashboard():
    if 'doctor_logged_in' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('doctor.doctor_login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    return render_template('doctor/dashboard.html', doctor=doctor)

@doctor_bp.route('/profile')
def doctor_profile():
    if 'doctor_logged_in' not in session:
        flash('Please login to access your profile.', 'warning')
        return redirect(url_for('doctor.doctor_login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    return render_template('doctor/profile.html', doctor=doctor)

@doctor_bp.route('/logout')
def doctor_logout():
    session.pop('doctor_logged_in', None)
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('doctor.doctor_login'))
