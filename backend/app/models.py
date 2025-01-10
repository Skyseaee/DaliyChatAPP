import uuid
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    daily_summary = db.Column(db.Text)
    monthly_summary = db.Column(db.Text)
    user_id = db.Column(db.String(36), db.ForeignKey('users.user_id'))
    user = db.relationship('User', backref=db.backref('diary_entries', lazy='dynamic'))
