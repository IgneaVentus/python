from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_login import LoginManager, UserMixin,login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "3970d1f589ad312fd01495377a661350"
db = SQLAlchemy(app)
from app import routes, models, scripts
from app.models import User, Post, Comment, Subforum, Error