from flask import Flask, render_template
from flask_mail import Mail, Message
from dotenv import dotenv_values
from Model import *

get_env = dotenv_values(".env")  

app = Flask(__name__)
# db = SQLAlchemy(app)

# app.config['MAIL_TLS_VERSION'] = 'TLSv1.2'
app.config['MAIL_SERVER'] = get_env['MAIL_SERVER']
app.config['MAIL_PORT'] = int(get_env['MAIL_PORT'])
app.config['MAIL_USE_TLS'] = get_env.get('MAIL_USE_TLS', '').lower() == 'true'
app.config['MAIL_USE_SSL'] = get_env['MAIL_USE_SSL'].lower() != 'false'
app.config['MAIL_USERNAME'] = get_env['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = get_env['MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = get_env['MAIL_DEFAULT_SENDER']
app.config['DEBUG'] = True

def send_notification_email(to, subject, body):
    mail = Mail(app)    
    with app.app_context():
        # print(users.id)
        message = Message(subject, recipients=[to], html=body)
        try:
            mail.send(message)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
