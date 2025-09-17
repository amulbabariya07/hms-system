from flask import render_template, request, redirect, url_for, flash, session, jsonify
from . import admin_bp, ADMIN_USERNAME, ADMIN_PASSWORD

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

@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Logged out.', 'info')
    return redirect(url_for('admin.admin_login'))

