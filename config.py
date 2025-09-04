import os

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://amul_flask:amul123@localhost/hms-system'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    RAZORPAY_KEY_ID = 'rzp_test_RCbfCPgiV69xNy'
    RAZORPAY_KEY_SECRET = '3RRL55fPNAqYZUk5YWfQdhwO'
    FLASK_SECRET_KEY = 'change-this-to-a-random-secret'
