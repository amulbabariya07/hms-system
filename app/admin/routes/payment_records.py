from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Payment, Appointment
from . import admin_bp

# Payment Records view
@admin_bp.route('/payment-records', methods=['GET'])
def admin_payment_records():
    search = request.args.get('search', '').strip()
    query = Payment.query.join(Appointment)
    if search:
        query = query.filter(Appointment.patient_name.ilike(f'%{search}%'))
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payment_records.html', payments=payments)
