from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# 导入模型和路由
from app import models

with app.app_context():
    db.create_all()

from app import routes
