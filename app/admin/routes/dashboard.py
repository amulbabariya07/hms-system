from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Appointment, Doctor, User
from . import admin_bp

@admin_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash('Please login to access dashboard.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    from datetime import date
    
    # Get statistics
    today = date.today()
    today_appointments = Appointment.query.filter(Appointment.appointment_date == today).count()
    total_appointments = Appointment.query.count()
    total_doctors = Doctor.query.filter_by(is_verified=True).count()
    pending_doctors = Doctor.query.filter_by(is_verified=False).count()
    total_patients = User.query.count()
    
    stats = {
        'today_appointments': today_appointments,
        'total_appointments': total_appointments,
        'total_doctors': total_doctors,
        'pending_doctors': pending_doctors,
        'total_patients': total_patients
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/configuration')
def admin_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))
    return render_template('admin/configuration.html')
