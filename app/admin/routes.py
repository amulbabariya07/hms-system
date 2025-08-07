from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from app import db
import re

import pyotp
import qrcode
import io
import base64

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Admin credentials (store securely in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# TOTP secret (In production, save this securely in DB or env file)
TOTP_SECRET = pyotp.random_base32()
TOTP_EMAIL = "amulbabariya121@gmail.com"


@admin_bp.route('/login')
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/login.html')


@admin_bp.route('/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('Please enter both username and password.', 'danger')
        return render_template('admin/login.html')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['temp_logged_in'] = True  # Intermediate auth step
        return redirect(url_for('admin.admin_authenticator'))
    else:
        flash('Invalid username or password. Please try again.', 'danger')
        return render_template('admin/login.html')


@admin_bp.route('/authenticator')
def admin_authenticator():
    if 'temp_logged_in' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('admin.admin_login'))

    # Generate TOTP and QR code
    totp = pyotp.TOTP(TOTP_SECRET)
    provisioning_url = totp.provisioning_uri(name=TOTP_EMAIL, issuer_name="HMS Admin Panel")

    # Generate QR code as base64
    qr = qrcode.make(provisioning_url)
    buf = io.BytesIO()
    qr.save(buf)
    buf.seek(0)
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render_template('admin/authenticator.html', qr_code=qr_b64)


@admin_bp.route('/authenticator', methods=['POST'])
def admin_authenticator_post():
    if 'temp_logged_in' not in session:
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('admin.admin_login'))

    code = request.form.get('code', '').strip()
    totp = pyotp.TOTP(TOTP_SECRET)

    if totp.verify(code):
        session.pop('temp_logged_in', None)
        session['admin_logged_in'] = True
        session['admin_username'] = ADMIN_USERNAME
        flash('Login successful with Google Authenticator.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        flash('Invalid authentication code. Please try again.', 'danger')
        return redirect(url_for('admin.admin_authenticator'))


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('temp_logged_in', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash('Please login to access the admin dashboard.', 'warning')
        return redirect(url_for('admin.admin_login'))

    return render_template('admin/dashboard.html', admin_username=session.get('admin_username'))


@admin_bp.route('/configuration')
def admin_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access this page.', 'warning')
        return redirect(url_for('admin.admin_login'))

    return render_template('admin/configuration.html', admin_username=session.get('admin_username'))
