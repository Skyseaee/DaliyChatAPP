from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CORS
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})  # This will allow all origins, which is fine for development


db = SQLAlchemy(app)

# 导入模型和路由
from app import models

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Import routes after db setup
from app import routes
