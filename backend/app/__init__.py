from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CORS
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})  # This will allow all origins, which is fine for development

@app.after_request
def after_request(response):
    # 添加跨域相关的响应头
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


db = SQLAlchemy(app)

# 导入模型和路由
from app import models

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Import routes after db setup
from app import routes
