from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Appointment, Doctor, User
from . import admin_bp
from datetime import datetime
from sqlalchemy import desc

@admin_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash('Please login to access dashboard.', 'warning')
        return redirect(url_for('admin.admin_login'))

    from datetime import date
    
    today = date.today()
    stats = {
        'today_appointments': Appointment.query.filter(Appointment.appointment_date == today).count(),
        'total_appointments': Appointment.query.count(),
        'total_doctors': Doctor.query.filter_by(is_verified=True).count(),
        'pending_doctors': Doctor.query.filter_by(is_verified=False).count(),
        'total_patients': User.query.count()
    }

    recent_activity = get_recent_activity(limit=5)

    return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity)

@admin_bp.route('/configuration')
def admin_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))
    return render_template('admin/configuration.html')

from flask import request, render_template
from math import ceil

from math import ceil
from flask import request, render_template
from . import admin_bp
from app.models import Appointment, User, Doctor
from sqlalchemy import desc

@admin_bp.route('/admin/recent-activity')
def recent_activity():
    page = request.args.get('page', 1, type=int)
    per_page = 15

    # Fetch all recent activities
    activities = []

    # Appointments
    appointments = Appointment.query.order_by(desc(Appointment.created_at)).all()
    for appt in appointments:
        activities.append({
            "type": "appointment",
            "patient_name": appt.patient_name,
            "doctor_name": appt.doctor.full_name,
            "department": appt.doctor.specialization.name if appt.doctor.specialization else "",
            "status": appt.get_display_status(),
            "time": appt.created_at
        })

    # Patients
    patients = User.query.order_by(desc(User.created_at)).all()
    for p in patients:
        activities.append({
            "type": "patient",
            "name": p.full_name,
            "time": p.created_at
        })

    # Doctors
    doctors = Doctor.query.order_by(desc(Doctor.created_at)).all()
    for d in doctors:
        activities.append({
            "type": "doctor",
            "name": d.full_name,
            "department": d.specialization.name if d.specialization else "",
            "time": d.created_at
        })

    # Sort by time descending
    activities.sort(key=lambda x: x["time"], reverse=True)

    # Pagination
    total = len(activities)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_activities = activities[start:end]
    total_pages = ceil(total / per_page)

    return render_template(
        "admin/recent_activity.html",
        recent_activity=paginated_activities,
        page=page,
        total_pages=total_pages
    )


def get_recent_activity(limit=5):
    recent_activity = []

    # New appointments
    appointments = Appointment.query.order_by(desc(Appointment.created_at)).limit(limit).all()
    for appt in appointments:
        recent_activity.append({
            'type': 'appointment',
            'patient_name': appt.patient_name,
            'doctor_name': appt.doctor.full_name,
            'department': appt.doctor.specialization.name if appt.doctor.specialization else "",
            'status': appt.get_display_status(),
            'time': appt.created_at
        })

    # New patients
    patients = User.query.order_by(desc(User.created_at)).limit(limit).all()
    for p in patients:
        recent_activity.append({
            'type': 'patient',
            'name': p.full_name,
            'time': p.created_at
        })

    # New doctors
    doctors = Doctor.query.order_by(desc(Doctor.created_at)).limit(limit).all()
    for d in doctors:
        recent_activity.append({
            'type': 'doctor',
            'name': d.full_name,
            'department': d.specialization.name if d.specialization else "",
            'time': d.created_at
        })

    # Sort all events by time descending
    recent_activity.sort(key=lambda x: x['time'], reverse=True)

    # Limit the number of records
    return recent_activity[:limit]
