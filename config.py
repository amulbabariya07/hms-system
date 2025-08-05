import os

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://amul_flask:amul123@localhost/hms-system'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
