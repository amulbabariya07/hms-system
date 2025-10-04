from app.admin.mail_setting import get_mail_settings
import smtplib
from email.mime.text import MIMEText

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, Doctor, Appointment, ContactQuery
from datetime import datetime
import re

receptionist_bp = Blueprint('receptionist', __name__, template_folder='templates')

# Receptionist credentials - Updated to use session-based credentials from admin panel
def get_receptionist_credentials():
    """Get receptionist credentials from session or use defaults"""
    if 'receptionist_credentials' in session:
        return session['receptionist_credentials']['username'], session['receptionist_credentials']['password']
    return "amul", "amul"  # Default credentials

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

def login_required(f):
    """Decorator to require login for receptionist routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'receptionist_logged_in' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('receptionist.receptionist_login'))
        return f(*args, **kwargs)
    return decorated_function

@receptionist_bp.route('/login')
def receptionist_login():
    if 'receptionist_logged_in' in session:
        return redirect(url_for('receptionist.receptionist_dashboard'))
    return render_template('receptionist/login.html')

@receptionist_bp.route('/login', methods=['POST'])
def receptionist_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    receptionist_username, receptionist_password = get_receptionist_credentials()

    if username == receptionist_username and password == receptionist_password:
        session['receptionist_logged_in'] = True
        session['receptionist_username'] = receptionist_username
        flash('Login successful. Welcome to Receptionist Panel!', 'success')
        return redirect(url_for('receptionist.receptionist_dashboard'))
    else:
        flash('Invalid credentials. Please try again.', 'danger')
        return render_template('receptionist/login.html')

@receptionist_bp.route('/logout')
def receptionist_logout():
    session.pop('receptionist_logged_in', None)
    session.pop('receptionist_username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('receptionist.receptionist_login'))

@receptionist_bp.route('/dashboard')
@login_required
def receptionist_dashboard():
    try:
        total_patients = User.query.count() if User else 0
        total_appointments = Appointment.query.count() if Appointment else 0
        today_appointments = Appointment.query.filter(
            Appointment.appointment_date == datetime.now().date()
        ).count() if Appointment else 0
        
        # Get statistics for queries
        total_queries = ContactQuery.query.count()
        new_queries = ContactQuery.query.filter_by(status='new').count()
        in_progress_queries = ContactQuery.query.filter_by(status='in_progress').count()
        resolved_queries = ContactQuery.query.filter_by(status='resolved').count()
        
        stats = {
            'total': total_queries,
            'new': new_queries,
            'in_progress': in_progress_queries,
            'resolved': resolved_queries
        }
        
    except:
        total_patients = 0
        total_appointments = 0
        today_appointments = 0
        stats = {'total': 0, 'new': 0, 'in_progress': 0, 'resolved': 0}
    
    return render_template('receptionist/dashboard.html', 
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         today_appointments=today_appointments,
                         stats=stats)

@receptionist_bp.route('/patients')
@login_required
def receptionist_patients():
    try:
        patients = User.query.all() if User else []
    except:
        patients = []
    return render_template('receptionist/patients.html', patients=patients)

@receptionist_bp.route('/patients/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name')
            mobile_number = request.form.get('mobile_number')
            email = request.form.get('email')
            password = request.form.get('password', 'default123')  # Default password for patients
            
            # Create new patient using User model
            new_patient = User(
                full_name=full_name,
                mobile_number=mobile_number,
                email=email,
                password=password
            )
            
            db.session.add(new_patient)
            db.session.commit()
            
            flash(f'Patient {full_name} has been successfully added!', 'success')
            return redirect(url_for('receptionist.receptionist_patients'))
            
        except Exception as e:
            flash(f'Error adding patient: {str(e)}', 'danger')
            db.session.rollback()
    
    return render_template('receptionist/add_patient.html')

@receptionist_bp.route('/patients/details/<int:patient_id>')
@login_required
def receptionist_patient_details(patient_id):
    try:
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
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching patient details'})

@receptionist_bp.route('/patients/edit/<int:patient_id>', methods=['POST'])
@login_required
def receptionist_edit_patient(patient_id):
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

@receptionist_bp.route('/appointments')
@login_required
def receptionist_appointments():
    try:
        appointments = Appointment.query.all() if Appointment else []
    except:
        appointments = []
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
    return render_template('receptionist/appointments.html', appointments=appointments)

@receptionist_bp.route('/appointments/create', methods=['GET', 'POST'])
@login_required
def create_appointment():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            doctor_id = request.form.get('doctor_id')
            patient_name = request.form.get('patient_name')
            appointment_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
            appointment_time = datetime.strptime(request.form.get('appointment_time'), '%H:%M').time()
            reason = request.form.get('reason')
            
            # Create new appointment
            new_appointment = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                patient_name=patient_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=reason,
                status='scheduled'
            )
            
            db.session.add(new_appointment)
            db.session.commit()
            
            flash('Appointment has been successfully created!', 'success')
            return redirect(url_for('receptionist.receptionist_appointments'))
            
        except Exception as e:
            flash(f'Error creating appointment: {str(e)}', 'danger')
            db.session.rollback()
    
    try:
        patients = User.query.all() if User else []
        doctors = Doctor.query.filter_by(is_verified=True).all() if Doctor else []
    except:
        patients = []
        doctors = []
    
    return render_template('receptionist/create_appointment.html', patients=patients, doctors=doctors)

@receptionist_bp.route('/appointments/details/<int:appointment_id>')
@login_required
def receptionist_appointment_details(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        return jsonify({
            'success': True,
            'appointment': {
                'id': appointment.id,
                'patient_name': appointment.user.full_name if appointment.user else 'N/A',
                'patient_mobile': appointment.user.mobile_number if appointment.user else 'N/A',
                'doctor_name': appointment.doctor.full_name if appointment.doctor else 'N/A',
                'doctor_specialization': appointment.doctor.specialization if appointment.doctor else 'N/A',
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else 'N/A',
                'appointment_time': appointment.appointment_time.strftime('%H:%M') if appointment.appointment_time else 'N/A',
                'symptoms': appointment.symptoms if hasattr(appointment, 'symptoms') else 'N/A',
                'status': appointment.status,
                'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching appointment details'})

@receptionist_bp.route('/appointments/edit/<int:appointment_id>', methods=['POST'])
@login_required
def receptionist_edit_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        symptoms = request.form.get('symptoms', '')
        status = request.form.get('status')

        # Validation
        if not all([appointment_date, appointment_time, status]):
            return jsonify({'success': False, 'message': 'Date, time and status are required.'})

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
        if hasattr(appointment, 'symptoms'):
            appointment.symptoms = symptoms
        appointment.status = status

        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment updated successfully!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the appointment.'})

@receptionist_bp.route('/appointments/delete/<int:appointment_id>', methods=['POST'])
@login_required
def receptionist_delete_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment deleted successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while deleting the appointment.'})


# New routes for patients queries management
@receptionist_bp.route('/queries')
@login_required
def patients_queries():
    """Display all patient queries with filtering and sorting options"""
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        query_type_filter = request.args.get('query_type', 'all')
        view_type = request.args.get('view', 'list')  # list or kanban
        
        # Base query
        queries = ContactQuery.query
        
        # Apply filters
        if status_filter != 'all':
            queries = queries.filter(ContactQuery.status == status_filter)
        if priority_filter != 'all':
            queries = queries.filter(ContactQuery.priority == priority_filter)
        if query_type_filter != 'all':
            queries = queries.filter(ContactQuery.query_type == query_type_filter)
        
        # Order by created_at descending (newest first)
        queries = queries.order_by(ContactQuery.created_at.desc()).all()
        
        # Get statistics for dashboard
        total_queries = ContactQuery.query.count()
        new_queries = ContactQuery.query.filter_by(status='new').count()
        in_progress_queries = ContactQuery.query.filter_by(status='in_progress').count()
        resolved_queries = ContactQuery.query.filter_by(status='resolved').count()
        
        stats = {
            'total': total_queries,
            'new': new_queries,
            'in_progress': in_progress_queries,
            'resolved': resolved_queries
        }
        
    except Exception as e:
        flash(f'Error loading queries: {str(e)}', 'danger')
        queries = []
        stats = {'total': 0, 'new': 0, 'in_progress': 0, 'resolved': 0}
    
    return render_template('receptionist/patients_queries.html', 
                         queries=queries, 
                         stats=stats,
                         current_status=status_filter,
                         current_priority=priority_filter,
                         current_query_type=query_type_filter,
                         view_type=view_type)

@receptionist_bp.route('/queries/<int:query_id>')
@login_required
def view_query(query_id):
    """View individual query details"""
    try:
        query = ContactQuery.query.get_or_404(query_id)
    except:
        flash('Query not found.', 'danger')
        return redirect(url_for('receptionist.patients_queries'))
    
    return render_template('receptionist/view_query.html', query=query)

@receptionist_bp.route('/queries/<int:query_id>/update', methods=['POST'])
@login_required
def update_query(query_id):
    """Update query status, priority, or add response"""
    try:
        query = ContactQuery.query.get_or_404(query_id)
        
        # Update fields from form
        if 'status' in request.form:
            query.status = request.form.get('status')
        if 'priority' in request.form:
            query.priority = request.form.get('priority')
        if 'assigned_to' in request.form:
            query.assigned_to = request.form.get('assigned_to')
        if 'response' in request.form:
            query.response = request.form.get('response')
        
        # Set resolved_at if status is resolved
        if query.status == 'resolved' and not query.resolved_at:
            query.resolved_at = datetime.utcnow()
        
        query.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Query updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating query: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('receptionist.view_query', query_id=query_id))

@receptionist_bp.route('/queries/<int:query_id>/delete', methods=['POST'])
@login_required
def delete_query(query_id):
    """Delete a query (admin action)"""
    try:
        query = ContactQuery.query.get_or_404(query_id)
        db.session.delete(query)
        db.session.commit()
        flash('Query deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting query: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('receptionist.patients_queries'))


@receptionist_bp.route('/queries/<int:query_id>/details')
@login_required
def get_query_details(query_id):
    """Return patient query details as JSON for modal popup"""
    try:
        query = ContactQuery.query.get_or_404(query_id)
        created_at = query.created_at.strftime('%Y-%m-%d %H:%M') if query.created_at else ''
        resolved_at = query.resolved_at.strftime('%Y-%m-%d %H:%M') if query.resolved_at else ''
        updated_at = query.updated_at.strftime('%Y-%m-%d %H:%M') if query.updated_at else ''
        return jsonify({
            'success': True,
            'query': {
                'id': query.id,
                'name': query.name,
                'email': query.email,
                'phone': query.phone,
                'query_type': query.query_type,
                'priority': query.priority,
                'status': query.status,
                'message': query.message,
                'created_at': created_at,
                'resolved_at': resolved_at,
                'updated_at': updated_at,
                'assigned_to': query.assigned_to
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching query details'})


@receptionist_bp.route('/queries/<int:query_id>/reply', methods=['POST'])
@login_required
def reply_to_query(query_id):
    data = request.get_json()
    message = data.get('message')
    recipient_email = data.get('email')

    if not message or not recipient_email:
        return jsonify({'success': False, 'message': 'Message or email missing'}), 400

    try:
        query = ContactQuery.query.get_or_404(query_id)
        sender_name = query.name or "User"

        subject = f"Healthcare+ | {sender_name}, Your Query Answer is Ready!"

        html_body = render_template(
            'email/query_reply_email.html',
            name=sender_name,
            message=message
        )

        mail_config = get_mail_settings()
        required_fields = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_EMAIL']
        missing = [field for field in required_fields if not mail_config.get(field)]
        if missing:
            return jsonify({
                'success': False,
                'message': 'Email configuration is incomplete. Please ask the admin to set up email settings in the Email Configuration panel before sending replies.'
            }), 400

        msg = MIMEText(html_body, "html")
        msg['Subject'] = subject
        name = mail_config['MAIL_DEFAULT_NAME']
        email = mail_config['MAIL_DEFAULT_EMAIL']
        msg['From'] = f"{name} <{email}>"
        msg['To'] = recipient_email

        server = smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT'])
        if mail_config['MAIL_USE_TLS']:
            server.starttls()
        server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
        server.sendmail(mail_config['MAIL_DEFAULT_EMAIL'], [recipient_email], msg.as_string())
        server.quit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred while sending the reply. Please check your email configuration or try again later.'})