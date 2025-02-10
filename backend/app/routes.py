from flask import request, jsonify, make_response
from app import app, db
from app.models import DiaryEntry, User
from app.vector_db import get_all_conversations, add_conversation
from app.openai_utils import generate_summary
import jwt
from datetime import datetime, timedelta

SECRET_KEY = app.config['SECRET_KEY']

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


# 对话路由
@app.route('/conversation', methods=['POST'])
def conversation():
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

    user_input = request.json.get('input')
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # 调用 OpenAI 获取回复
    response = generate_summary(user_input)
    bot_response = response.choices[0].message.content

    # 将对话记录存储到向量数据库
    add_conversation(user_id, user_input + " " + bot_response)

    return jsonify({"response": bot_response})


# 生成每日总结路由
@app.route('/generate_daily_summary', methods=['POST'])
def generate_daily_summary():
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

    # 从向量数据库获取当天所有对话
    all_conversations = get_all_conversations(user_id)

    # 调用 OpenAI 生成每日总结
    daily_summary = generate_summary(f"请对以下内容进行总结：{all_conversations}")
    daily_summary = daily_summary.choices[0].message.content

    # 存储每日总结到关系型数据库
    new_entry = DiaryEntry(date=request.json.get('date'), daily_summary=daily_summary, user_id=user_id)
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"daily_summary": daily_summary})


# 生成每月总结路由
@app.route('/generate_monthly_summary', methods=['POST'])
def generate_monthly_summary():
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

    # 从关系型数据库获取当月所有每日总结
    month = request.json.get('month')
    year = request.json.get('year')
    daily_summaries = DiaryEntry.query.filter(
        DiaryEntry.date.startswith(f"{year}-{month}"),
        DiaryEntry.user_id == user_id
    ).all()
    all_daily_summaries = " ".join([entry.daily_summary for entry in daily_summaries])

    # 调用 OpenAI 生成每月总结
    monthly_summary = generate_summary(f"请对以下每日总结进行月度总结：{all_daily_summaries}")
    monthly_summary = monthly_summary.choices[0].message.content

    # 更新关系型数据库中的月度总结
    for entry in daily_summaries:
        entry.monthly_summary = monthly_summary
    db.session.commit()

    return jsonify({"monthly_summary": monthly_summary})


# 获取日记路由
@app.route('/diary', methods=['GET'])
def get_diary():
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

    date = request.args.get('date')
    if date:
        entry = DiaryEntry.query.filter_by(date=date, user_id=user_id).first()
        if entry:
            return jsonify({
                "date": entry.date,
                "daily_summary": entry.daily_summary,
                "monthly_summary": entry.monthly_summary
            })
        else:
            return jsonify({"error": "No diary entry found for the given date"}), 404
    else:
        all_entries = DiaryEntry.query.filter_by(user_id=user_id).all()
        diary_list = []
        for entry in all_entries:
            diary_list.append({
                "date": entry.date,
                "daily_summary": entry.daily_summary,
                "monthly_summary": entry.monthly_summary
            })
        return jsonify(diary_list)
