from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
# import mysql.connector
from sqlalchemy import create_engine
from dotenv import dotenv_values


get_env = dotenv_values(".env")  
app = Flask(__name__)

DB_URL = get_env['DB_URL']

engine = create_engine(DB_URL)
# print(engine)
# Example: Connect to the database and execute a simple query
# with engine.connect() as connection:
#     result = connection.execute ("SELECT '* From User'")
#     print(result.scaler())


app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False