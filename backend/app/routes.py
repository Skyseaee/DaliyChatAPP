from typing import Generator
from flask import Response, request, jsonify, make_response
from app import app, db
from app.models import DailyDiaryEntry, User, MonthlyDiaryEntry
from app.vector_db import get_all_conversations, add_conversation
from app.openai_utils import generate_summary
import jwt
from datetime import datetime, time, timedelta
from functools import wraps
# from flask_socketio import SocketIO, send

SECRET_KEY = app.config['SECRET_KEY']
# socketio = SocketIO(app)

# JWT 鉴权装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        token = token.replace('Bearer ', '')

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(user_id, *args, **kwargs)
    return decorated

# 用户注册路由
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": "Username already exists"}), 409

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

# 用户登录路由
@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})

    user = User.query.filter_by(username=auth.username).first()
    if not user or not user.check_password(auth.password):
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})

    token = jwt.encode({
        'user_id': user.user_id,
        'exp': datetime.utcnow() + timedelta(minutes=30)
    }, SECRET_KEY)

    return jsonify({'token': token})

@app.route('/conversation', methods=['POST'])
@token_required
def conversation(user_id):

    user_input = request.json.get('input')
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    response = generate_summary(user_input)

    if isinstance(response, Generator):  # 如果是生成器（stream=True）
        return jsonify({"error": "Unexpected stream response"}), 500
    else:  # 如果是普通响应（stream=False）
        bot_response = response.choices[0].message.content
        add_conversation(user_id, user_input + " " + bot_response)
        return jsonify({"response": bot_response})

# @app.route('/conversation', methods=['POST'])
# def conversation():
#     user_input = request.json.get('input')
#     if not user_input:
#         return jsonify({"error": "No input provided"}), 400
    
#     # Start processing the user input (replace with your logic)
#     response = generate_summary(user_input, stream=True)

#     # Send chunks of response via WebSocket
#     for part in response:
#         socketio.emit('bot_response', {'data': part})
    
#     return jsonify({"status": "processing"})

# @socketio.on('connect')
# def handle_connect():
#     print("Client connected")


# 生成每日总结路由
@app.route('/generate_daily_summary', methods=['POST'])
@token_required
def generate_daily_summary(user_id):
    all_conversations = get_all_conversations(user_id)
    daily_summary = generate_summary(f"请对以下内容进行总结：{all_conversations}")
    daily_summary = daily_summary.choices[0].message.content

    new_entry = DailyDiaryEntry(date=request.json.get('date'), daily_summary=daily_summary, user_id=user_id)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"daily_summary": daily_summary})


# 生成每月总结路由
@app.route('/generate_monthly_summary', methods=['POST'])
@token_required
def generate_monthly_summary(user_id):
    month = request.json.get('month')
    year = request.json.get('year')
    daily_summaries = DailyDiaryEntry.query.filter(
        DailyDiaryEntry.date.startswith(f"{year}-{month}"),
        DailyDiaryEntry.user_id == user_id
    ).all()
    all_daily_summaries = " ".join([entry.daily_summary for entry in daily_summaries])

    monthly_summary = generate_summary(f"请对以下每日总结进行月度总结：{all_daily_summaries}")
    monthly_summary = monthly_summary.choices[0].message.content

    new_entry = MonthlyDiaryEntry(month=f"{year}-{month}", monthly_summary=monthly_summary, user_id=user_id)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"monthly_summary": monthly_summary})


# 获取日记路由
@app.route('/diary', methods=['GET'])
@token_required
def get_diary(user_id):
    date = request.args.get('date')
    if date:
        daily_entry = DailyDiaryEntry.query.filter_by(date=date, user_id=user_id).first()
        if daily_entry:
            return jsonify({
                "date": daily_entry.date,
                "daily_summary": daily_entry.daily_summary
            })
        else:
            return jsonify({"error": "No daily diary entry found for the given date"}), 404
    else:
        all_daily_entries = DailyDiaryEntry.query.filter_by(user_id=user_id).all()
        daily_entries_list = [
            {"date": entry.date, "daily_summary": entry.daily_summary} for entry in all_daily_entries
        ]
        
        all_monthly_entries = MonthlyDiaryEntry.query.filter_by(user_id=user_id).all()
        monthly_entries_list = [
            {"month": entry.month, "monthly_summary": entry.monthly_summary} for entry in all_monthly_entries
        ]
        
        return jsonify({
            "daily_entries": daily_entries_list,
            "monthly_entries": monthly_entries_list
        })

