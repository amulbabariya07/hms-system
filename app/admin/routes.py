from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db  # adjust as needed
# import pyotp
# import qrcode
# import io
# import base64

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Temporary fake "DB"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
CURRENT_EMAIL = "httpsbabariya121@gmail.com"

admin_store = {
    "username": "admin",
    "password": "admin",  # use hash in production
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
        session['admin_logged_in'] = True
        session['admin_username'] = ADMIN_USERNAME
        flash('Login successful.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        flash('Invalid credentials.', 'danger')
        return render_template('admin/login.html')


# @admin_bp.route('/authenticator')
# def admin_authenticator():
#     # This route is no longer needed
#     return redirect(url_for('admin.admin_dashboard'))


# @admin_bp.route('/authenticator', methods=['POST'])
# def admin_authenticator_post():
#     # This route is no longer needed
#     return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
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
