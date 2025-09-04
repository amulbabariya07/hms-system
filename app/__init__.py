from app.payment.routes import payment_bp
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

    @app.route('/about')
    def about():
        from app.models import Doctor
        doctors = Doctor.query.filter_by(is_verified=True).all()
        return render_template('about.html', doctors=doctors)

    @app.route('/services')
    def services():
        return render_template('services.html')

    @app.route('/appointment')
    def appointment():
        return render_template('appointment.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        from app.models import ContactQuery, db
        from flask import request, flash, redirect, url_for
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            message = request.form['message']
            query = ContactQuery(name=name, email=email, phone=phone, message=message)
            db.session.add(query)
            db.session.commit()
            flash('Your message has been sent!')
            return redirect(url_for('contact'))
        return render_template('contact.html')

    from app.patient.routes import patient_bp
    app.register_blueprint(patient_bp, url_prefix='/patient')

    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.doctor.routes import doctor_bp
    app.register_blueprint(doctor_bp, url_prefix='/doctor')

    from app.receptionist.routes import receptionist_bp
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')

    app.register_blueprint(payment_bp, url_prefix='/payment')

    from app import models
    with app.app_context():
        db.create_all()

    return app
