# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app import db
from app.models import User, DailyDiaryEntry, MonthlyDiaryEntry
from app.openai_utils import seek_chat_service
from datetime import datetime
from app.vector_db import get_all_conversations

# 初始化调度器
scheduler = BackgroundScheduler()

# 每日总结任务
def generate_daily_summaries():
    users = User.query.all()
    for user in users:
        # 获取所有用户对话内容
        all_conversations = get_all_conversations(user.user_id)
        daily_summary = seek_chat_service(f"请对以下内容进行总结：{all_conversations}")
        daily_summary = daily_summary.choices[0].message.content
        
        # 保存每日总结
        new_entry = DailyDiaryEntry(date=datetime.utcnow().strftime('%Y-%m-%d'), 
                                    daily_summary=daily_summary, user_id=user.user_id)
        db.session.add(new_entry)
    db.session.commit()

# 每月总结任务
def generate_monthly_summaries():
    users = User.query.all()
    for user in users:
        today = datetime.utcnow()
        month = today.strftime('%Y-%m')
        
        daily_summaries = DailyDiaryEntry.query.filter(
            DailyDiaryEntry.date.startswith(month), 
            DailyDiaryEntry.user_id == user.user_id
        ).all()
        
        all_daily_summaries = " ".join([entry.daily_summary for entry in daily_summaries])
        
        monthly_summary = seek_chat_service(f"请对以下每日总结进行月度总结：{all_daily_summaries}")
        monthly_summary = monthly_summary.choices[0].message.content

        # 保存月度总结
        new_entry = MonthlyDiaryEntry(month=month, monthly_summary=monthly_summary, user_id=user.user_id)
        db.session.add(new_entry)
    db.session.commit()

# 配置调度器定时任务
scheduler.add_job(generate_daily_summaries, CronTrigger(hour=0, minute=0))  # 每日0点执行
scheduler.add_job(generate_monthly_summaries, CronTrigger(day=1, hour=0, minute=0))  # 每月1号0点执行

# 启动调度器
scheduler.start()
