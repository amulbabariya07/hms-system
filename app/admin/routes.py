from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import re

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Admin credentials (in production, store these securely)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

@admin_bp.route('/login')
def admin_login():
    # If admin is already logged in, redirect to a simple success page
    if 'admin_logged_in' in session:
        return render_template('admin/login.html', logged_in=True)
    return render_template('admin/login.html')

@admin_bp.route('/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please enter both username and password.', 'danger')
        return render_template('admin/login.html')
    
    # Check credentials
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        session['admin_username'] = username
        flash(f'Welcome back, Administrator! Login successful.', 'success')
        return render_template('admin/login.html', logged_in=True)
    else:
        flash('Invalid username or password. Please try again.', 'danger')
        return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('admin.admin_login'))
