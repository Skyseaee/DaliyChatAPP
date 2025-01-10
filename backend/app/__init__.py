from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from chatAI.backend.config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

from app import models, routes