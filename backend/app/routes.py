from datetime import datetime, timedelta
from typing import Dict, List, Union
from flask import request, jsonify, make_response
from functools import wraps
import jwt
from app import app, db
from app.models import DailyDiaryEntry, User, MonthlyDiaryEntry
from app.vector_db import get_all_conversations, add_conversation
from app.openai_utils import generate_summary
from sqlalchemy import extract, and_

# 错误处理统一格式
def handle_error(message: str, code: int):
    return jsonify({"success": False, "error": message}), code

# 增强的JWT鉴权装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return handle_error("Authorization token required", 401)
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if not user:
                return handle_error("User not found", 404)
            request.user = user
        except jwt.ExpiredSignatureError:
            return handle_error("Token expired", 401)
        except jwt.InvalidTokenError:
            return handle_error("Invalid token", 401)
        except Exception as e:
            app.logger.error(f"Authentication error: {str(e)}")
            return handle_error("Internal server error", 500)
            
        return f(*args, **kwargs)
    return decorated

# 注册接口增强
@app.route('/api/v1/register', methods=['POST'])
def register():
    data: Dict = request.get_json()
    if not data:
        return handle_error("Invalid JSON data", 400)
    
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return handle_error("Username and password required", 400)
    
    if User.query.filter_by(username=username).first():
        return handle_error("Username already exists", 409)
    
    try:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "success": True,
            "user_id": new_user.user_id
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Registration error: {str(e)}")
        return handle_error("Could not create user", 500)

# 登录接口增强
@app.route('/api/v1/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return handle_error("Basic auth required", 401)
    
    user = User.query.filter_by(username=auth.username).first()
    if not user or not user.check_password(auth.password):
        return handle_error("Invalid credentials", 401)
    
    try:
        token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(hours=2)
        }, app.config['SECRET_KEY'])
        
        return jsonify({'token': token, 'user_id': user.user_id})
    except Exception as e:
        app.logger.error(f"Token generation error: {str(e)}")
        return handle_error("Could not generate token", 500)

# 增强的对话接口
@app.route('/api/v1/conversation', methods=['POST'])
@token_required
def conversation():
    data: Dict = request.get_json()
    if not data or 'input' not in data:
        return handle_error("Missing conversation input", 400)
    
    try:
        response = generate_summary(data['input'])
        user_id = data['user_id']
        # if not response or 'choices' not in response:
        #     return handle_error("Failed to generate response", 500)
            
        bot_response = response.choices[0].message.content
        
        add_conversation(user_id, f"Q: {data['input']} A: {bot_response}")
        
        return jsonify({
            "success": True,
            "response": bot_response
        })
    except Exception as e:
        app.logger.error(f"Conversation error: {str(e)}")
        return handle_error("Internal server error", 500)

# 增强的日记接口
@app.route('/api/v1/diaries', methods=['GET'])
@token_required
def get_diary():
    date = request.args.get('date')
    user_id = request.args.get('user_id')
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

# 新增月度总结接口
@app.route('/api/v1/monthly-summaries', methods=['GET'])
@token_required
def get_monthly_summaries():
    year = request.args.get('year')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)

    query = MonthlyDiaryEntry.query.filter_by(user_id=request.user.user_id)
    
    if year:
        try:
            year = int(year)
            query = query.filter(extract('year', MonthlyDiaryEntry.month) == year)
        except ValueError:
            return handle_error("Invalid year parameter", 400)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    summaries = [{
        "month": entry.month.strftime("%Y-%m"),
        "summary": entry.monthly_summary,
        "created_at": entry.created_at.isoformat()
    } for entry in pagination.items]
    
    return jsonify({
        "success": True,
        "data": summaries,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages
        }
    })

@app.route('/api/v1/monthly-diaries', methods=['GET'])
@token_required
def get_daily_summaries():
    # 获取请求参数
    year = request.args.get('year')
    month = request.args.get('month')
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)  # 默认每页15条
    try:
        # 处理日期过滤
        if year and month:
            # 验证参数有效性
            year_int = int(year)
            month_int = int(month)
            # if not (1 <= month_int <= 12):
            #     raise ValueError
            date_prefix = f"{year}-{month}-"
        else:
            # 默认获取当前月份
            today = datetime.utcnow()
            date_prefix = today.strftime("%Y-%m-")
            year_int = today.year
            month_int = today.month

        # 构建查询
        query = DailyDiaryEntry.query.filter(
            DailyDiaryEntry.user_id == user_id,
            DailyDiaryEntry.date.startswith(date_prefix)
        ).order_by(DailyDiaryEntry.date.desc())
        # print(query)
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 构建响应数据
        summaries = [{
            "date": entry.date,
            "daily_summary": entry.daily_summary,
        } for entry in pagination.items]

        return jsonify({
            "success": True,
            "data": {
                "year": year_int,
                "month": month_int,
                "entries": summaries
            },
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages
            }
        })

    except ValueError:
        return handle_error("Invalid year/month parameters", 400)
    except Exception as e:
        app.logger.error(f"Error fetching daily summaries: {str(e)}")
        return handle_error("Server error", 500)

@app.route('/api/v1/yearly-monthly-diaries', methods=['GET'])
@token_required
def get_yearly_monthly_summaries():
    # 获取请求参数
    year = request.args.get('year')
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)  # 默认每页12条

    try:
        # 验证年份参数
        if year:
            year_int = int(year)
            if year_int < 1900 or year_int > 2100:  # 简单年份范围验证
                raise ValueError
        else:
            # 默认获取当前年份
            today = datetime.utcnow()
            year_int = today.year

        # 构建查询
        query = MonthlyDiaryEntry.query.filter(
            MonthlyDiaryEntry.user_id == user_id,
            MonthlyDiaryEntry.month.startswith(f"{year_int}-")  # 过滤指定年份
        ).order_by(MonthlyDiaryEntry.month.desc())

        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 构建响应数据
        summaries = [{
            "month": entry.month,
            "monthly_summary": entry.monthly_summary,
        } for entry in pagination.items]

        return jsonify({
            "success": True,
            "data": {
                "year": year_int,
                "entries": summaries
            },
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages
            }
        })

    except ValueError:
        return handle_error("Invalid year parameter", 400)
    except Exception as e:
        app.logger.error(f"Error fetching yearly monthly summaries: {str(e)}")
        return handle_error("Server error", 500)

# 增强的月度总结生成
@app.route('/api/v1/generate-monthly-summary', methods=['POST'])
@token_required
def generate_monthly_summary():
    data: Dict = request.get_json()
    if not data:
        return handle_error("Invalid JSON data", 400)
    
    required_fields = ['year', 'month']
    if not all(field in data for field in required_fields):
        return handle_error("Missing required fields: year, month", 400)
    
    try:
        year = int(data['year'])
        month = int(data['month'])
        if not (1 <= month <= 12):
            raise ValueError
    except ValueError:
        return handle_error("Invalid year/month parameters", 400)
    
    try:
        # 获取当月的所有日记
        entries = DailyDiaryEntry.query.filter(
            extract('year', DailyDiaryEntry.date) == year,
            extract('month', DailyDiaryEntry.date) == month,
            DailyDiaryEntry.user_id == request.user.user_id
        ).all()
        
        if not entries:
            return handle_error("No diary entries found for this month", 404)
        
        # 生成总结
        summaries = "\n".join([e.daily_summary for e in entries])
        gpt_response = generate_summary(f"请生成{year}年{month}月的月度总结，基于以下日记：\n{summaries}")
        
        if not gpt_response or 'choices' not in gpt_response:
            return handle_error("Failed to generate summary", 500)
            
        monthly_summary = gpt_response.choices[0].message.content
        
        # 保存到数据库
        existing = MonthlyDiaryEntry.query.filter_by(
            month=datetime(year, month, 1).date(),
            user_id=request.user.user_id
        ).first()
        
        if existing:
            existing.monthly_summary = monthly_summary
        else:
            new_entry = MonthlyDiaryEntry(
                month=datetime(year, month, 1).date(),
                monthly_summary=monthly_summary,
                user_id=request.user.user_id
            )
            db.session.add(new_entry)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "month": f"{year}-{month:02d}",
            "summary": monthly_summary
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Monthly summary error: {str(e)}")
        return handle_error("Internal server error", 500)

# 统一错误处理
@app.errorhandler(404)
def not_found(error):
    return handle_error("Resource not found", 404)

@app.errorhandler(500)
def internal_error(error):
    return handle_error("Internal server error", 500)