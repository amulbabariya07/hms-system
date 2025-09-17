from flask import Blueprint
from .medical_record import patient_medical_bp

patient_bp = Blueprint('patient', __name__, template_folder='templates')

def register_patient_blueprints(app):
    app.register_blueprint(patient_medical_bp)
