from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db  # adjust as needed
import pyotp
import qrcode
import io
import base64

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Temporary fake "DB"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
CURRENT_EMAIL = "httpsbabariya121@gmail.com"

# Fake admin DB simulation (you should replace with real DB)
admin_store = {
    "username": "admin",
    "password": "admin",  # use hash in production
    "totp_secret": pyotp.random_base32(),
    "totp_email": None,
    "qr_shown": False
}


@admin_bp.route('/login')
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/login.html')


@admin_bp.route('/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['temp_logged_in'] = True
        return redirect(url_for('admin.admin_authenticator'))
    else:
        flash('Invalid credentials.', 'danger')
        return render_template('admin/login.html')


@admin_bp.route('/authenticator')
def admin_authenticator():
    if 'temp_logged_in' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('admin.admin_login'))

    admin = admin_store
    totp_secret = admin['totp_secret']
    stored_email = admin.get('totp_email')
    qr_shown = admin.get('qr_shown')

    # Show QR code only if:
    # 1. It was never shown before
    # 2. Or the email has changed
    if not qr_shown or stored_email != CURRENT_EMAIL:
        totp = pyotp.TOTP(totp_secret)
        provisioning_url = totp.provisioning_uri(name=CURRENT_EMAIL, issuer_name="HMS Admin Panel")

        # Generate QR
        qr_img = qrcode.make(provisioning_url)
        buf = io.BytesIO()
        qr_img.save(buf)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # Save updated QR/email status
        admin['qr_shown'] = True
        admin['totp_email'] = CURRENT_EMAIL

        return render_template('admin/authenticator_qr.html', qr_code=qr_b64)

    # If already shown — just show code entry page
    return render_template('admin/authenticator_input.html')


@admin_bp.route('/authenticator', methods=['POST'])
def admin_authenticator_post():
    if 'temp_logged_in' not in session:
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('admin.admin_login'))

    code = request.form.get('code', '').strip()
    totp = pyotp.TOTP(admin_store['totp_secret'])

    if totp.verify(code):
        session.pop('temp_logged_in', None)
        session['admin_logged_in'] = True
        session['admin_username'] = ADMIN_USERNAME
        flash('Login successful.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        flash('Invalid code. Please try again.', 'danger')
        return redirect(url_for('admin.admin_authenticator'))


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('temp_logged_in', None)
    flash('Logged out.', 'info')
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash('Please login to access dashboard.', 'warning')
        return redirect(url_for('admin.admin_login'))
    return render_template('admin/dashboard.html')


@admin_bp.route('/configuration')
def admin_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))
    return render_template('admin/configuration.html')
