from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CORS
from config import Config
import logging
import click
from flask.cli import with_appcontext


app = Flask(__name__)
app.config.from_object(Config)

# flask insert-test-data
@app.cli.command("insert-test-data")
@with_appcontext
def insert_test_data():
    """Insert test data into the database."""
    from app.models import User, DailyDiaryEntry, MonthlyDiaryEntry
    from werkzeug.security import generate_password_hash

    # 插入用户数据
    user1 = User(
        user_id='550e8400-e29b-41d4-a716-446655440000',
        username='user1',
        password_hash=generate_password_hash('password1', method="pbkdf2:sha256")
    )
    user2 = User(
        user_id='550e8400-e29b-41d4-a716-446655440001',
        username='user2',
        password_hash=generate_password_hash('password2', method="pbkdf2:sha256")
    )
    db.session.add(user1)
    db.session.add(user2)

    # 插入每日日记数据
    daily_entry1 = DailyDiaryEntry(
        date='2025-02-18',
        daily_summary='今天是一个忙碌的工作日，完成了几个重要的任务。',
        user_id='550e8400-e29b-41d4-a716-446655440000'
    )
    daily_entry2 = DailyDiaryEntry(
        date='2025-02-17',
        daily_summary='周末放松了一下，和家人一起去了公园散步。',
        user_id='550e8400-e29b-41d4-a716-446655440000'
    )
    db.session.add(daily_entry1)
    db.session.add(daily_entry2)

    # 插入每月日记数据
    monthly_entry1 = MonthlyDiaryEntry(
        month='2025-02',
        monthly_summary='二月是一个充满挑战的月份，完成了多个项目，感觉自己在不断进步。',
        user_id='550e8400-e29b-41d4-a716-446655440000'
    )
    monthly_entry2 = MonthlyDiaryEntry(
        month='2025-01',
        monthly_summary='一月是新年伊始，制定了新的目标，并开始逐步实施。',
        user_id='550e8400-e29b-41d4-a716-446655440000'
    )
    db.session.add(monthly_entry1)
    db.session.add(monthly_entry2)

    db.session.commit()
    print("Test data inserted successfully!")

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
    insert_test_data()

from app.scheduler import scheduler

# Import routes after db setup
from app import routes
