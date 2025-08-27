
# SMTP mail settings for Flask app (fetch from DB)
from app import db
from app.models import MailSetting

def get_mail_settings():
	settings = MailSetting.query.first()
	if settings:
		return {
			'MAIL_SERVER': settings.mail_server,
			'MAIL_PORT': settings.mail_port,
			'MAIL_USE_TLS': settings.mail_use_tls,
			'MAIL_USERNAME': settings.mail_username,
			'MAIL_PASSWORD': settings.mail_password,
			'MAIL_DEFAULT_NAME': settings.mail_default_name,
			'MAIL_DEFAULT_EMAIL': settings.mail_default_email
		}
	# fallback defaults
	return {
		'MAIL_SERVER': 'smtp.gmail.com',
		'MAIL_PORT': 587,
		'MAIL_USE_TLS': True,
		'MAIL_USERNAME': '',
		'MAIL_PASSWORD': '',
		'MAIL_DEFAULT_NAME': 'hms-system',
		'MAIL_DEFAULT_EMAIL': ''
	}
