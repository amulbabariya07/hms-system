from app.models import Payment, Appointment, Doctor, Specialization
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Payment, Appointment, Doctor, User, MailSetting, Specialization
from werkzeug.security import generate_password_hash
from datetime import datetime
import re

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Temporary fake "DB"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
CURRENT_EMAIL = "httpsbabariya121@gmail.com"

admin_store = {
    "username": "admin",
    "password": "admin",  # use hash in production
}

def clean_mobile_number(number):
    return re.sub(r'\D', '', number)

from . import appointments
from . import auth
from . import configuration
from . import dashboard
from . import doctors
from . import email_configuration
from . import patients
from . import payment_records
from . import specializations
