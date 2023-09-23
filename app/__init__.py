# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# initialize the app
app = Flask(__name__)

# Configuration for MySQL database
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "mysql://root:password@localhost:3306/store_app_db"

db = SQLAlchemy(app)  # Create the SQLAlchemy instance
