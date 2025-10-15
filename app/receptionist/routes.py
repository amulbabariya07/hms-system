from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import User, Doctor, Appointment, ContactQuery, PatientIntakeForm, MedicalPrescription, Medicine 
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
        search_query = request.args.get('search', '').strip()
        
        if search_query:
            # Search by patient name or mobile number
            patients = User.query.filter(
                (User.full_name.ilike(f'%{search_query}%')) | 
                (User.mobile_number.ilike(f'%{search_query}%'))
            ).all()
        else:
            patients = User.query.all() if User else []
    except Exception as e:
        patients = []
        flash(f'Error loading patients: {str(e)}', 'danger')
    
    return render_template('receptionist/patients.html', patients=patients, search_query=search_query)

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
        # Base user (from User model)
        user = User.query.get(patient_id)
        if not user:
            return jsonify({'success': False, 'message': 'Patient not found.'}), 404

        # Extended details (from PatientIntakeForm)
        intake = PatientIntakeForm.query.filter_by(created_by=str(user.id)).first()

        # Combine both sources
        patient_data = {
            'id': user.id,
            'full_name': user.full_name or 'N/A',
            'mobile_number': user.mobile_number or 'N/A',
            'email': user.email or 'N/A',
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A',
            'appointment_count': len(user.appointments) if hasattr(user, 'appointments') else 0,

            # From PatientIntakeForm (if available)
            'age': getattr(intake, 'age', 'N/A') if intake else 'N/A',
            'gender': getattr(intake, 'gender', 'N/A') if intake else 'N/A',
            'blood_group': getattr(intake, 'blood_group', 'N/A') if intake else 'N/A',
            'occupation': getattr(intake, 'occupation', 'N/A') if intake else 'N/A',
            'reason_for_visit': getattr(intake, 'reason_for_visit', 'N/A') if intake else 'N/A',
        }

        return jsonify({'success': True, 'patient': patient_data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error fetching patient details: {str(e)}'}), 500


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
        search_query = request.args.get('search', '').strip()
        date_filter = request.args.get('date', '').strip()
        status_filter = request.args.get('status', 'all')
        
        # Flag: are we showing today's appointments? Only apply smart ordering if date_filter is empty
        today_only = False
        if not date_filter:
            today_only = True
            date_filter = datetime.now().date().isoformat()  # default to today
        
        appointments_query = Appointment.query
        
        # Apply search filter
        if search_query:
            appointments_query = appointments_query.join(User).join(Doctor).filter(
                (User.full_name.ilike(f'%{search_query}%')) | 
                (Doctor.full_name.ilike(f'%{search_query}%')) |
                (Appointment.patient_name.ilike(f'%{search_query}%'))
            )
        
        # Apply date filter
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                appointments_query = appointments_query.filter(Appointment.appointment_date == filter_date)
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'warning')
        
        # Apply status filter
        if status_filter != 'all':
            appointments_query = appointments_query.filter(Appointment.status == status_filter)
        
        appointments = appointments_query.all()
        
        # Compute display status
        for appt in appointments:
            appt.display_status = appt.get_display_status() if hasattr(appt, 'get_display_status') else appt.status.title()
        
        # Smart ordering ONLY for today
        if today_only:
            under_consultation = [a for a in appointments if a.status == 'under_consultation']
            scheduled_today = [a for a in appointments if a.status == 'scheduled']
            completed_or_cancelled = [a for a in appointments if a.status in ['completed', 'cancelled']]
            # Concatenate lists: top highlighted, then scheduled, then completed
            appointments = under_consultation + scheduled_today + completed_or_cancelled

    except Exception as e:
        appointments = []
        flash(f'Error loading appointments: {str(e)}', 'danger')
    
    return render_template(
        'receptionist/appointments.html',
        appointments=appointments,
        search_query=search_query,
        date_filter=date_filter,
        status_filter=status_filter
    )


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

@receptionist_bp.route('/appointments/edit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appointment_page(appointment_id):
    """Edit appointment details via modal"""
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        if request.method == 'POST':
            try:
                # Get form data
                appointment_date = request.form.get('appointment_date')
                appointment_time = request.form.get('appointment_time')
                reason = request.form.get('reason')
                status = request.form.get('status')
                
                # Validation
                if not all([appointment_date, appointment_time, status]):
                    return jsonify({'success': False, 'message': 'All required fields must be filled.'})
                
                # Convert date and time
                try:
                    appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
                    appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
                except ValueError:
                    return jsonify({'success': False, 'message': 'Invalid date or time format.'})
                
                # Update appointment
                appointment.appointment_date = appointment_date
                appointment.appointment_time = appointment_time
                appointment.reason = reason
                appointment.status = status
                appointment.updated_at = datetime.utcnow()
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'Appointment updated successfully!'})
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Error updating appointment: {str(e)}'})
        
        # GET request - return appointment data
        return jsonify({
            'success': True,
            'appointment': {
                'id': appointment.id,
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else '',
                'appointment_time': appointment.appointment_time.strftime('%H:%M') if appointment.appointment_time else '',
                'reason': appointment.reason if appointment.reason else '',
                'status': appointment.status
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error loading appointment details: {str(e)}'})

@receptionist_bp.route('/appointments/update/<int:appointment_id>', methods=['POST'])
@login_required
def update_appointment(appointment_id):
    """Update appointment details"""
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        patient_name = request.form.get('patient_name')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason')
        status = request.form.get('status')

        # Validation
        if not all([patient_id, doctor_id, patient_name, appointment_date, appointment_time, status]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('receptionist.edit_appointment_page', appointment_id=appointment_id))

        if status not in ['scheduled', 'completed', 'cancelled', 'confirmed', 'under_consultation']:
            flash('Invalid status selected.', 'danger')
            return redirect(url_for('receptionist.edit_appointment_page', appointment_id=appointment_id))

        try:
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('receptionist.edit_appointment_page', appointment_id=appointment_id))

        # Update appointment information
        appointment.patient_id = patient_id
        appointment.doctor_id = doctor_id
        appointment.patient_name = patient_name
        appointment.appointment_date = appointment_date
        appointment.appointment_time = appointment_time
        appointment.reason = reason
        appointment.status = status
        appointment.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Appointment updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating appointment: {str(e)}', 'danger')
    
    return redirect(url_for('receptionist.receptionist_appointments'))

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
                'doctor_specialization': appointment.doctor.specialization if appointment.doctor and hasattr(appointment.doctor, 'specialization') else 'N/A',
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else 'N/A',
                'appointment_time': appointment.appointment_time.strftime('%H:%M') if appointment.appointment_time else 'N/A',
                'reason': appointment.reason if appointment.reason else 'N/A',
                'symptoms': appointment.symptoms if appointment.symptoms else 'N/A',
                'status': appointment.status,
                'display_status': appointment.get_display_status() if hasattr(appointment, 'get_display_status') else appointment.status.title(),
                'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S') if appointment.created_at else ''
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching appointment details: {str(e)}'})

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

@receptionist_bp.route('/queries')
@login_required
def patients_queries():
    status = request.args.get('status', 'new')          # default: 'new'
    priority = request.args.get('priority', 'all')
    query_type = request.args.get('query_type', 'all')
    view = request.args.get('view', 'list')             # default: 'list'

    # Filter your queries
    queries = ContactQuery.query
    if status != 'all':
        queries = queries.filter_by(status=status)
    if priority != 'all':
        queries = queries.filter_by(priority=priority)
    if query_type != 'all':
        queries = queries.filter_by(query_type=query_type)

    queries = queries.all()

    # Stats for cards
    stats = {
        'total': ContactQuery.query.count(),
        'new': ContactQuery.query.filter_by(status='new').count(),
        'in_progress': ContactQuery.query.filter_by(status='in_progress').count(),
        'resolved': ContactQuery.query.filter_by(status='resolved').count(),
    }

    return render_template('receptionist/patients_queries.html',
        stats=stats,
        queries=queries,
        current_status=status,
        current_priority=priority,
        current_query_type=query_type,
        view_type=view
    )

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
                'response': query.response or '',
                'created_at': created_at,
                'resolved_at': resolved_at,
                'updated_at': updated_at,
                'assigned_to': query.assigned_to or 'N/A'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching query details'})


@receptionist_bp.route('/queries/<int:query_id>/reply', methods=['POST'])
@login_required
def reply_to_query(query_id):
    from app.admin.mail_setting import get_mail_settings
    import smtplib
    from email.mime.text import MIMEText
    
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
        msg = MIMEText(html_body, "html")
        msg['Subject'] = subject
        msg['From'] = f"{mail_config['MAIL_DEFAULT_NAME']} <{mail_config['MAIL_DEFAULT_EMAIL']}>"
        msg['To'] = recipient_email

        server = smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT'])
        if mail_config['MAIL_USE_TLS']:
            server.starttls()
        server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
        server.sendmail(mail_config['MAIL_DEFAULT_EMAIL'], [recipient_email], msg.as_string())
        server.quit()

        # ✅ Auto mark as resolved once reply sent
        query.response = message
        query.status = 'resolved'
        query.resolved_at = datetime.utcnow()
        query.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@receptionist_bp.route('/patient/<int:patient_id>/intake-readonly')
@login_required
def patient_intake_readonly(patient_id):
    # Find appointment for this patient
    appointment = Appointment.query.filter_by(patient_id=patient_id).first()
    intake_form = None
    if appointment:
        # Intake form created_by matches patient id as string
        intake_form = PatientIntakeForm.query.filter_by(created_by=str(patient_id)).first()
    patient = User.query.get(patient_id)
    if not intake_form:
        return "No intake form found for this patient.", 404
    return render_template('doctor/patient_intake_readonly.html', intake=intake_form, patient=patient)

@receptionist_bp.route('/prescription/<int:prescription_id>/view', methods=['GET'])
@login_required
def view_prescription_readonly(prescription_id):
    pres = MedicalPrescription.query.get_or_404(prescription_id)
    medicines = pres.medicines
    doctor = pres.doctor
    appointment = pres.appointment
    return render_template('doctor/prescription_readonly.html', prescription=pres, medicines=medicines, doctor=doctor, appointment=appointment)

@receptionist_bp.route('/appointment/<int:appointment_id>/prescription-info')
@login_required
def get_prescription_info(appointment_id):
    prescription = MedicalPrescription.query.filter_by(appointment_id=appointment_id).first()
    if prescription:
        return jsonify({
            'has_prescription': True,
            'prescription_id': prescription.id
        })
    else:
        return jsonify({'has_prescription': False})

@receptionist_bp.route('/patients/update/<int:patient_id>', methods=['POST'])
@login_required
def update_patient(patient_id):
    try:
        data = request.get_json()
        user = User.query.get(patient_id)
        if not user:
            return jsonify({'success': False, 'message': 'Patient not found.'}), 404

        # Update User model fields
        user.full_name = data.get('full_name', user.full_name)
        user.email = data.get('email', user.email)
        user.mobile_number = data.get('mobile_number', user.mobile_number)

        # Update or create PatientIntakeForm record
        intake = PatientIntakeForm.query.filter_by(created_by=str(user.id)).first()
        if not intake:
            intake = PatientIntakeForm(created_by=str(user.id))
            db.session.add(intake)

        intake.age = data.get('age')
        intake.gender = data.get('gender')
        intake.blood_group = data.get('blood_group')
        intake.occupation = data.get('occupation')
        intake.reason_for_visit = data.get('reason_for_visit')

        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@receptionist_bp.route('/queries/<int:query_id>/check_reply')
def check_reply(query_id):
    query = ContactQuery.query.get_or_404(query_id)
    has_reply = bool(query.response and query.response.strip())
    return jsonify({'has_reply': has_reply})
