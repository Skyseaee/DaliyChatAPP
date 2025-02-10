import os
import configparser
import secrets

# create ConfigParser 
config = configparser.ConfigParser()
config.read('config.ini')

flask_config = config['flask_config']

class Config:
    SQLALCHEMY_DATABASE_URI = flask_config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///diary.db')
    # 从配置文件中获取 SQLALCHEMY_TRACK_MODIFICATIONS，并将其转换为布尔值
    SQLALCHEMY_TRACK_MODIFICATIONS = flask_config.getboolean('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", flask_config.get('OPENAI_API_KEY'))
    SECRET_KEY = os.environ.get('SECRET_KEY', flask_config.get('SECRET_KEY', 'your_secret_key')) or secrets.token_hex(32)