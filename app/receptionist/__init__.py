from flask import Blueprint

receptionist_bp = Blueprint('receptionist', __name__, template_folder='templates')

from app.receptionist import routes
