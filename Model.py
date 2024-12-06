
from asyncio.log import logger
import email
from enum import unique
import hashlib
from locale import currency
import requests
from telnetlib import STATUS
from textwrap import indent
from time import timezone
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import defer, undefer, relationship, load_only, sessionmaker
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import DeclarativeMeta
from Helper.helper import generate_referance
from Settings import app
from datetime import datetime, timedelta
# from flask_script import Manager
from flask_migrate import Migrate
import json
# from sendEmail import Email 
import uuid
import sys
from dotenv import dotenv_values
from sqlalchemy import inspect, func, or_
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin


get_env = dotenv_values(".env") 
db = SQLAlchemy(app)
migrate = Migrate(app, db)




# Initialize Flask-Admin
admin = Admin(app, name='Admin Dashboard', template_mode='bootstrap4')


# Define Roles and Users
# roles_users = db.Table('roles_users',
#     db.Column('user_id', db.Integer, db.ForeignKey('inv_user.id')),
#     db.Column('role_id', db.Integer, db.ForeignKey('inv_role.id'))
# )

 
list_account_status = ['PENDING', 'APPROVED', 'REJECTED']
list_status_evaluation = ["PENDING", "STARTED", "REJECTED", "COMPLETED"]
list_other_info = ["user_preference_email", "user_preference_phone", "purpose_evaluation", "institution_name", "department_office", "contact_person", "contact_person_email", "payment_method", "billing_address", "verification_status", "reference_email", "reference_phone", "school_year_to", "school_year_from", "gpa", "major_study", "degree_obtained" ]

def get_location(ip_address):
    response = requests.get(f"https://ipinfo.io/{ip_address}/json")
    data = response.json()
    return data

def alchemy_to_json(obj, visited=None):
    if visited is None:
        visited = set()
    if id(obj) in visited:
        return None  # Prevent infinite recursion
    visited.add(id(obj))
    
    if isinstance(obj.__class__, DeclarativeMeta):
        fields = {}
        # Determine the role and exclude fields accordingly
        if hasattr(obj, 'role'):
            exclude_fields = ["query", "registry", "query_class", "password", "student"]
        else:
            exclude_fields = ["query", "registry", "query_class", "password"]

        for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata' and x not in exclude_fields]:
            data = getattr(obj, field)
            try:
                if not callable(data):
                    # Handle SQLAlchemy relationships
                    if isinstance(data.__class__, DeclarativeMeta):
                        fields[field] = alchemy_to_json(data, visited)
                    elif isinstance(data, list) and data and isinstance(data[0].__class__, DeclarativeMeta):
                        fields[field] = [alchemy_to_json(item, visited) for item in data]
                    else:
                        # this will fail on non-encodable values, like other classes
                        json.dumps(data)
                        fields[field] = data
                else:
                    pass
            except TypeError:
                fields[field] = str(data)
        return fields
    else:
        return obj


# class Inv_Role(db.Model, RoleMixin):
#     __tablename__ = 'inv_role'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(80), unique=True)
    
class Inv_User(db.Model):
    __tablename__ = 'inv_user'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    other_name = db.Column(db.String(80), nullable=True)
    active_status = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    address = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    other_info = db.Column(JSON, nullable=True)
    active = db.Column(db.Boolean())
    # roles = db.relationship('Role', secondary=roles_users, backref=db.backref('inv_user', lazy='dynamic'))
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    inv_file = db.relationship('Inv_Fileupload', back_populates='inv_user', lazy='select')
    inv_usage = db.relationship('Inv_Usage',  back_populates='inv_user', lazy='joined')
    
    def json(self):
        return {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'phone': self.phone, 
                'country': self.country,
                'address': self.address, 
                'other_info': self.other_info,
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'created_on': str(self.created_on),
                'updated_on': str(self.updated_on),
                'file': [inv_file.to_dict() for inv_file in self.inv_file]
                }
    def _repr_(self):
        return json.dumps({
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'country': self.country, 
                'other_info': self.other_info,
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'created_on': self.created_on,
                'updated_on': self.updated_on })

    def username_password_match(_username, _password ):
        new_data = Inv_User.query.filter_by(email=_username, password=_password).first()
        print(">>>", new_data)
        if new_data is None:
            return False
        elif new_data:
            new_data_object = alchemy_to_json(new_data)
            return new_data_object
        else:
            new_data_object = new_data.json()
            return new_data_object

    def getAllUsers(page, per_page):        
        # Determine the page and number of items per page from the request (if provided)
        # Query the database with pagination
        pagination = Inv_User.query.paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items for the current page
        new_data = pagination.items
        # Render nested objects
        new_data_object = [alchemy_to_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        pagination_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': new_data_object,
            'pagination': pagination_data
        }

    def getUserById(id):
        new_data = Inv_User.query.filter_by(id=id).first()
        new_data_object = new_data.json()
        return new_data_object

    def getUserByEmail(email):
        new_data = Inv_User.query.filter_by(email=email).first()
        new_data_object = alchemy_to_json(new_data)
        return new_data_object

    def getAllUsersByEmail(_email):
        joined_table_data = []
        # user_data = db.session.query(Inv_User).filter_by(email=_email).join(Business).all()
        # user_data = db.session.query(Inv_User, Business).filter_by(email=_email).join(Business).all()
        user_data = db.session.query(Inv_User).filter_by(email=_email).all()

        # get joined tables data .
        for user in user_data:
            joined_table_data.append({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name, 
                    'last_name': user.last_name, 
                    'other_name': user.other_name, 
                    'country': user.country, 
                    'created_by': user.created_by,
                    'updated_by': user.updated_by,
                    'created_on': user.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_on': user.updated_on.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        # Convert the result to a JSON-formatted string
        result_json = json.dumps(joined_table_data, indent=2)
        return  result_json

    def createUser(_first_name, _last_name, _other_name, _password, _email, _description, _address, **kwargs):
        user_id = str(uuid.uuid4())

        new_user = Inv_User( email=_email, password=_password, first_name=_first_name, last_name=_last_name, other_name=_other_name, created_by=_email, updated_by=_email, id=user_id, address=_address)
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.close()
            pass
        return new_user

    def update_user( _id, _value, _user_data):
        _user_data = Inv_User.query.filter_by(id=_id).first()
        _user_data.password = hashlib.sha256((_value).encode()).hexdigest()
        db.session.commit()
        return True

    def update_email_user( _email, _value, _user_data):
        _user_data = Inv_User.query.filter_by(email=_email).first()
        _user_data.password = hashlib.sha256((_value).encode()).hexdigest()
        db.session.commit()
        return True

    def update_user_any(user_id, updated_by, **kwargs):
        try:
            with app.app_context():
                user = db.session.query(Inv_User).filter(Inv_User.id == user_id).one_or_none() or []
                if user:
                    for key, value in kwargs.items():
                        # allow for other info
                        if key in list_other_info:
                            if user.other_info:
                                user.other_info = user.other_info | {key: value}
                            else:
                                user.other_info = {key: value}
                        else:
                            setattr(user, key, value)
                    user.updated_on = datetime.utcnow()
                    user.updated_by = updated_by
                    db.session.commit()
                    logger.info(f"user updated with ID: {user.id}")
                else:
                    logger.warning(f"No user found with ID: {user_id}")
                return user.json()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {e}")
            raise


    def delete_user(_id):
        is_successful = Inv_User.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

class Inv_Usage(db.Model):
    __tablename__ = 'inv_usage'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=True)
    info = db.Column(JSON, nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the Inv_User table
    user_id = db.Column(db.String(36), db.ForeignKey('inv_user.id'))
    # Define a relationship to access the Inv_User object from a Inv_User object
    inv_user = db.relationship('Inv_User', back_populates='inv_usage', lazy='select')

    def usage_json(self):
        return {
                'id': self.id,
                'type': self.type,
                'browser': self.info['browser'],
                'ip': self.info['ip'].split(",")[0],
                'browser_version': self.info['browser_version'],
                'os': self.info['os'],
                'os_version': self.info['os_version'],
                'device': self.info['device'],
                'is_mobile': self.info['is_mobile'],
                'is_tablet': self.info['is_tablet'],
                'is_pc': self.info['is_pc'],
                'is_bot': self.info['is_bot'],
                'geo': self.info.get('ip_data') if self.info.get('ip_data') else get_location(self.info.get('ip').split(",")[0]),
                'created_on': str(self.created_on),
                'updated_on': str(self.updated_on) }

    def getAllUsage(search, page, per_page, status, start_date, end_date): 
        # base query_other
        query_other = Inv_Usage.query
        # filter
        if search:
            query_other = query_other.filter(
                or_(
                    Inv_Usage.type.ilike(f'%{search}%'),
                    Inv_Usage.id.ilike(f'%{search}%'),
                )
            )
        
        if start_date:
            query_other = query_other.filter( Inv_Usage.created_on >= start_date )
        if end_date:
            query_other = query_other.filter(Inv_Usage.created_on <= end_date)
        query_other = query_other.order_by(Inv_Usage.created_on.desc())  
        pagination = query_other.paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items list for the current page
        new_data = pagination.items
        # Render nested objects
        pagination_data = [Inv_Usage.usage_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        paging_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        previous = None
        next = None
        if pagination.has_next:
            next = f"{get_env['PAGING_PATH_BASE']}evaluation-paging?page={ pagination.next_num }&per_page={ pagination.per_page }&search={ search }"
        if pagination.has_prev:
            previous = f"{get_env['PAGING_PATH_BASE']}evaluation-paging?page={ pagination.prev_num }&per_page={ pagination.per_page }&search={ search }"

        return {
            'data': pagination_data,
            'pagination': paging_data,
            'previous': previous,
            'next': next
        }



    def create_usage(info, type, user_id):
        _id = str(uuid.uuid4())
        try:
            usage = Inv_Usage(id=_id, info=info, type=type, user_id=user_id)
            db.session.add(usage)
            db.session.commit()
            logger.info(f"Inv_Usage created with ID: {usage.id}")
            return usage
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating application: {e}")
            raise


class Inv_Code(db.Model):
    __tablename__ = 'inv_code'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    code = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    account = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def createCode(_email, _code, _type):
        # cron job to delete expired used user sessions
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        Inv_Code.query.filter(Inv_Code.updated_on <= cutoff_time).delete()
        db.session.commit()

        _id = str(uuid.uuid4())
        new_data = Inv_Code( account=_email, code=_code, type=_type, id=_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_data)
                db.session.commit()
        except Exception as e:
            # db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.commit()
            # db.session.close()
            pass
        return new_data
    
    def delete_email_code(_code, _email):
        is_successful = Inv_Code.query.filter_by(account=_email, code=_code).delete()
        db.session.commit()
        return bool(is_successful)
    
    def delete_code(_id):
        is_successful = Inv_Code.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

    def getCodeByOTP(_otp, email):
        if Inv_Code.query.filter_by(code=_otp).filter_by(account=email).first():
            return Inv_Code.query.filter_by(code=_otp).filter_by(account=email).first()
        else:
            return None

    # get transacttion by ID
    def getCodeById(id, page=1, per_page=10):        
        # Determine the page and number of items per page from the request (if provided)
        # Query the database with pagination
        pagination = Inv_Code.query.filter_by(id=id).paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items for the current page
        new_data = pagination.items
        # Render nested objects
        new_data_object = [alchemy_to_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        pagination_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': new_data_object,
            'pagination': pagination_data
        }

class Inv_Fileupload(db.Model):
    __tablename__ = 'inv_file'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    file = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    format = db.Column(db.String(80), nullable=True)
    issued_date = db.Column(db.DateTime(), nullable=True)
    slug = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the user table
    user_id = db.Column(db.String(36), db.ForeignKey('inv_user.id'))    
    inv_user = db.relationship('Inv_User', back_populates='inv_file', lazy='select')
    
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.file,
            'type': self.type,
            'format': self.format,
            'issued_date': str(self.issued_date),
            'url': get_env['FILE_STATIC_UPLOAD_PATH_READ'] + str(self.id) + '.' + self.format,
            'slug': self.slug,
            'description': self.description,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on)
        }

    def countFileById(user_id):
        return Inv_Fileupload.query.filter_by(user_id=user_id).count()
    
    def get_type_file(user_id, file_type):
        try:
            data_get = db.session.query(Inv_Fileupload).filter(Inv_Fileupload.user_id == user_id, Inv_Fileupload.type == file_type).first() or {}

            logger.info(f"Retrieved {data_get} {file_type}")
            return {
                'file': data_get.to_dict(),
                'status': True
            }
        except Exception as e:
            logger.error(f"Error retrieving: {e}")
            return {
                'file': "file not found",
                'status': False,
                'error': str(e)
            }

    # get file by business
    def getFileById(id, page=1, per_page=10): 
        pagination = Inv_Fileupload.query.filter_by(id=id).paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items for the current page
        new_data = pagination.items
        # Render nested objects
        new_data_object = [alchemy_to_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        pagination_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }    
        return {
            'data': new_data_object,
            'pagination': pagination_data
        }

    def createFile(_file, _description, _file_type, _doc_format, _user_id, _issued_date, _slug):
        _id = str(uuid.uuid4())
        print("---------")
        new_data = Inv_Fileupload( file=_file, description=_description, id=_id, type=_file_type, format=_doc_format, user_id=_user_id, issued_date=_issued_date, slug=_slug)

        try:
            if new_data:
                # Start a new session
                db.session.add(new_data)
                db.session.commit()
                return new_data.to_dict()
            else:
                return new_data
        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            # print(f"Error:: {e}")
        finally:
            # db.session.close()
            pass
 
    def updateFile(file, description, business, id):
        new_data = Inv_Fileupload.query.filter_by(id=id).first()
        if file:
            new_data.file = file
        if description:
            new_data.description = description
        db.session.commit()
        return alchemy_to_json(new_data)

    def delete_file(_id):
        is_successful = Inv_Fileupload.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)




# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, Inv_User, Inv_Role)
security = Security(app, user_datastore)

# Add Views to Admin
admin.add_view(ModelView(Inv_User, db.session))
# admin.add_view(ModelView(Product, db.session))