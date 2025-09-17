from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import MailSetting
from . import admin_bp

@admin_bp.route('/email-configuration', methods=['GET', 'POST'])
def email_configuration():
    if 'admin_logged_in' not in session:
        flash('Please login to access Email Configuration.', 'warning')
        return redirect(url_for('admin.admin_login'))

    mail_setting = MailSetting.query.first()
    if request.method == 'POST':
        mail_server = request.form.get('mail_server')
        mail_port = request.form.get('mail_port', type=int)
        mail_use_tls = request.form.get('mail_use_tls') == 'True'
        mail_username = request.form.get('mail_username')
        mail_password = request.form.get('mail_password')
        mail_default_name = request.form.get('mail_default_name')
        mail_default_email = request.form.get('mail_default_email')

        if mail_setting:
            mail_setting.mail_server = mail_server
            mail_setting.mail_port = mail_port
            mail_setting.mail_use_tls = mail_use_tls
            mail_setting.mail_username = mail_username
            mail_setting.mail_password = mail_password
            mail_setting.mail_default_name = mail_default_name
            mail_setting.mail_default_email = mail_default_email
        else:
            mail_setting = MailSetting(
                mail_server=mail_server,
                mail_port=mail_port,
                mail_use_tls=mail_use_tls,
                mail_username=mail_username,
                mail_password=mail_password,
                mail_default_name=mail_default_name,
                mail_default_email=mail_default_email
            )
            db.session.add(mail_setting)
        db.session.commit()
        flash('Email configuration updated successfully.', 'success')
        return redirect(url_for('admin.email_configuration'))

    return render_template('admin/email_configuration.html', mail_setting=mail_setting)
