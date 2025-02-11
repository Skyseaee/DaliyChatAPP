from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CORS
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})  # This will allow all origins, which is fine for development

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


db = SQLAlchemy(app)

# 导入模型和路由
from app import models

# Create tables if they don't exist
with app.app_context():
    db.create_all()

from app.scheduler import scheduler

# Import routes after db setup
from app import routes
