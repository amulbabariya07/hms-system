from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Add the home route
    @app.route('/')
    def home():
        return render_template('home.html')

    from app.patient.routes import patient_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app import models
    with app.app_context():
        db.create_all()

    return app
