import os

class Config:
    SQLALCHEMY_DATABASE_URI ='sqlite:///diary.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
