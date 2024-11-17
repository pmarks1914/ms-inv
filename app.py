from crypt import methods
import math
import re
import uuid
from flask import Flask, jsonify, request, Response, render_template, url_for
import requests, json
from Helper.helper import generate_random_code
from fileManager.fileManager import fileUploadManager
#import geocoder
from Model import Inv_Usage, Inv_User, Inv_Code, db, Inv_Fileupload, get_location
from Notification.Email.sendEmail import send_notification_email
# from sendEmail import Email 
from Settings import *
import jwt, datetime
# from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from functools import wraps
from flask_cors import CORS
import hashlib
# from pyisemail import is_email 
import sys
#import winrt.windows.devices.geolocation as wdg, asyncio
from email.mime.text import MIMEText
#from safrs import SAFRSBase, SAFRSAPI
#from api_spec import spec
#from swagger import swagger_ui_blueprint, SWAGGER_URL
# Created instance of the class
from dotenv import dotenv_values
from user_agents import parse


get_env = dotenv_values(".env")  

CORS(app)
# CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = get_env['SECRET_KEY']
 

def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        token = token.split(" ")[1]        
        if not token:
            return jsonify({'error': 'Token is missing', 'code': 401}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e), 'code': 401}), 401
    return wrapper

def return_user_id(request):
    token = request.headers.get('Authorization')
    msg = {}
    token = token.split(" ")[1]        
    token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
    user_id = token_data['id'] or None
    return user_id

def get_device_info(request, type, user_id):
    # Extract device details
    user_agent = request.headers.get('User-Agent')
    # Get the client's IP address
    ip=None
    ip_data=None

    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
        ip_data = get_location(ip.split(",")[0])
    else:
        ip = request.remote_addr
        ip_data = get_location(ip.split(",")[0])
    # Parse the User-Agent string using the user_agents library
    ua = parse(user_agent)
    device_info = {
        "browser": ua.browser.family,
        "browser_version": ua.browser.version_string,        
        "os": ua.os.family, 
        "os_version": ua.os.version_string,
        "device": ua.device.family,
        "is_mobile": ua.is_mobile, 
        "is_tablet": ua.is_tablet,  
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot, 
        "ip": ip,
        "ip_data": ip_data
    }
    Inv_Usage.create_usage(device_info, type, user_id)
    
@app.route('/test', methods=['GET'])
# @token_required
def testd():
    try:
        # Extract query parameters
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)
        user = Inv_User.getAllUsers(page, per_page)

        msg = {
            "code": 200,
            "message": 'Successful',
            "user": user['data'],
            "pagination": user['pagination']
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response    
    except Exception as e:
        return {"tes": str(e)}


@app.route('/token/status', methods=['GET'])
# @token_required
def token_status():
    msg = {
            "code": 404,
            "status": False,
            "message": "Failed",
        }
    try:
        user_id = return_user_id(request)
        user = Inv_User.getUserById(user_id)
        msg = {
            "code": 200,
            "status": True,
            "message": 'Successful',
            "user": user,
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response    
    except Exception as e:
        # return {"tes": str(e)}
        response = Response( json.dumps(msg | {"error": str(e)} ), status=200, mimetype='application/json')
        return response 

@app.route('/v1/callback/mfs', methods=['POST'])
def callbackfs():
    try:
        request_data = request.json
        msg = {
            "code": 200,
            "message": 'Successful',
            "data": request_data
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response 
    except Exception as e:
        return {"tes": str(e)}

@app.route('/login', methods=['POST'])
def get_student_login():
    count_stats = None
    file_photo = None
    request_data = request.get_json()
    get_device_info(request, "LOGIN", user_id=None)
    password_hashed = hashlib.sha256((request_data.get('password')).encode()).hexdigest()
    try:
        match = Inv_User.username_password_match(request_data.get('email'), password_hashed)
        if match != None and match != False:
            expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
            token = jwt.encode({'exp': expiration_date, 'id': match['id']}, app.config['SECRET_KEY'], algorithm='HS256')
            get_device_info(request, "LOGIN", user_id=match['id'])

            count_stats = {
                "file": Inv_Fileupload.countFileById(match['id'])
            }
            file_data_get = Inv_Fileupload.get_type_file(match['id'], "Photo")
            if file_data_get['status']:
                file_photo = file_data_get['file']['url']

            msg = { "user": match | {"count_stats": count_stats, "file_photo": file_photo }, "access_key": jwt.decode( token, app.config['SECRET_KEY'], algorithms=['HS256'] ), "token": token }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        else:
            invalidUserOjectErrorMsg= {"code": 404, "User unavailable": 'Failed'}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=404, mimetype='application/json')
    except Exception as e:
            invalidUserOjectErrorMsg= {"code": 500, "message": 'Failed', "error": str(e)}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=500, mimetype='application/json')

@app.route('/user/<string:id>', methods=['GET'])
@token_required
def user(id):
    if request.method == 'GET':
        try:
            request_data = Inv_User.getUserById(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
        
@app.route('/v1/registration', methods=['POST'])
def add_user_registration():
    request_data = request.get_json()
    get_device_info(request, "REGISTER", user_id=None)
    msg = {}
    code = request_data.get('otp')
    email = request_data.get('email')
    if request_data.get('password1') == None or request_data.get('email') == None:
        msg = {
            "code": 305,
            "message": 'Password or Email is required'
        }
        response = Response(json.dumps(msg), status=200, mimetype='application/json')
        return response 
    elif Inv_Code.getCodeByOTP(code, email) is None:
        return jsonify({ 'code': 403, 'message': 'Resource not found, check your email for the required code'}), 403

    try:
        _password = hashlib.sha256((request_data.get('password1')).encode()).hexdigest()
        _first_name = request_data.get('first_name')
        _last_name = request_data.get('last_name')
        _other_name = request_data.get('other_name')
        _email = request_data.get('email')
        _description = request_data.get('description')
        _address = request_data.get('address')

        if Inv_User.query.filter_by(email=request_data.get('email')).first() is not None:
            msg = {
                "code": 202,
                "error": "user already registtered"
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response
        else:
            Inv_User.createUser(_first_name, _last_name, _other_name, _password, _email, _description, _address )
            invalidUserOjectErrorMsg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    "first_name": request_data.get('first_name'),
                    "last_name": request_data.get('last_name'),
                    "other_name": request_data.get('other_name'),
                    "email": request_data.get('email'),
                    "description": request_data.get('description'),
                    "address": request_data.get('address')
                }
            }

            get_device_info(request, "REGISTER", user_id=request_data.get('id') )
            response = Response(json.dumps(invalidUserOjectErrorMsg), status=200, mimetype='application/json')
            return response
    except Exception as e:
        invalidUserOjectErrorMsg = {
            "code": 204,
            "error": str(e)
        }
        response = Response(json.dumps(invalidUserOjectErrorMsg), status=200, mimetype='application/json')
        return response
  
@app.route('/v1/change/password/<string:id>', methods=['PATCH'])
def update_password(id):
    # Fetch the resource from your data source (e.g., database)
    request_data = request.get_json()
    get_device_info(request, "PASSWORD-CHANGE")
    resource = Inv_User.getUserById(id)
    validate_list = ["id", "password1", "password2", "code", "email"]
    validate_status = False
    msg = {}
    if resource is None:
        return jsonify({ 'code': 404, 'error': 'Resource not found'}), 404
    elif Inv_Code.getCodeByOTP(request_data.get('code'), request_data.get('email') ) is None:
        return jsonify({ 'code': 403, 'error': 'Resource not found, check your email for the required code'}), 404
    # Get the data from the request
    data = request.get_json()
    get_req_keys = None
    get_req_keys_value_pair = None
    # Update only the provided fields
    for key, value in data.items():
        if key in validate_list:
            validate_status = True
            if get_req_keys is None:
                get_req_keys = key
                get_req_keys_value_pair = f'"{key}": "{value}"'
            else:
                get_req_keys = f"{get_req_keys}, {key}"
                get_req_keys_value_pair = f'{get_req_keys_value_pair}, "{key}": "{value}"'
  
    if validate_status is False:
        msg = {
            "code": 201,
            "message": str(validate_list)
        }
    else:
        try:
            if Inv_User.update_user( id, request_data.get('password1'), resource):
                get_device_info(request, "PASSWORD-CHANGE", user_id=id)
                msg = {
                        "code": 200,
                        "message": f"user detail(s) updated: {get_req_keys}",
                        # "data": 'f{instance_dict}'
                }
            else:
                msg = {
                    "code": 301,
                    "message": f"user detail(s) failed to updated.",
            }
        except Exception as e:
            msg = {
                    "code": 501,
                    "error :" : str(e),
                    "message": "server error." 
                }

    response = Response( json.dumps(msg), status=200, mimetype='application/json')
    return response  

@app.route('/v1/forget/password', methods=['PUT'])
def forget_password():
    # Fetch the resource from your data source (e.g., database)
    request_data = request.get_json()
    get_device_info(request, "PASSWORD-RESET")
    resource = Inv_User.getUserByEmail(request_data.get("email"))
    validate_list = ["password1", "password2", "code", "email"]
    validate_status = False
    msg = {}
    if resource is None:
        return jsonify({ 'code': 404, 'error': 'Resource not found'}), 404
    elif Inv_Code.getCodeByOTP(request_data.get('code'), request_data.get('email') ) is None:
        return jsonify({ 'code': 403, 'error': 'Resource not found, check your email for the required code'}), 404
    # Get the data from the request
    data = request.get_json()
    get_req_keys = None
    get_req_keys_value_pair = None
    # Update only the provided fields
    for key, value in data.items():
        if key in validate_list:
            validate_status = True
            if get_req_keys is None:
                get_req_keys = key
                get_req_keys_value_pair = f'"{key}": "{value}"'
            else:
                get_req_keys = f"{get_req_keys}, {key}"
                get_req_keys_value_pair = f'{get_req_keys_value_pair}, "{key}": "{value}"'  
    if validate_status is False:
        msg = {
            "code": 201,
            "message": str(validate_list)
        }
    else:
        try:
            if Inv_User.update_email_user( request_data.get("email"), request_data.get('password1'), resource):
                get_device_info(request, "PASSWORD-RESET", user_id=resource['id'])
                msg = {
                        "code": 200,
                        "status": True,
                        "message": f"user detail(s) updated: {get_req_keys}",
                }
                Inv_Code.delete_email_code(request_data.get('code'), request_data.get('email') )
            else:
                msg = {
                    "code": 301,
                    "message": f"user detail(s) failed to updated.",
            }
        except Exception as e:
            msg = {
                    "code": 501,
                    "error :" : str(e),
                    "message": "server error." 
                }
    response = Response( json.dumps(msg), status=200, mimetype='application/json')
    return response  
       
@app.route('/v1/otp/email', methods=['POST'])
def send_notification():
    data = request.get_json()
    to_email = data['email']
    subject = 'Notification Subject'
    users = Inv_User.query.filter_by(email=to_email).first()
    # print(users.id)
    if users is None:
        pass
    else:
        get_device_info(request, 'EMAIL-OTP', user_id=users.id)
    try:
        if users:
            return 'User exist.'
        else:
            code = generate_random_code()
            render_html = render_template('email.html', code=code)
            Inv_Code.createCode(to_email, code, "OTP")
            if send_notification_email(to_email, subject, render_html):
                return jsonify({ 'code': 200, 'msg': 'Notification sent successfully'}), 200
            else:
                return 'Failed to send notification.'
    except Exception as e:
        return str(e)

@app.route('/v1/send/otp/email', methods=['POST'])
def send_otp():
    data = request.get_json()
    to_email = data['email']
    get_device_info(request, 'EMAIL-OTP', user_id=None)
    subject = 'Notification Subject'
    users = Inv_User.query.filter_by(email=to_email).first()
    if users is None:
        pass
    else:
        get_device_info(request, 'EMAIL-OTP', user_id=users.id)
    try:
        code = generate_random_code()
        render_html = render_template('email.html', code=code)
        Inv_Code.createCode(to_email, code, "OTP")
        if send_notification_email(to_email, subject, render_html):
            return jsonify({ 'code': 200, 'msg': 'Notification sent successfully'}), 200
        else:
            return 'Failed to send notification.'
    except Exception as e:
        return str(e)

@app.route('/static/uploads')
def index():
    return render_template('/fileUpload.html')

# @app.route('/static/<string:file>')
# def upload_index_file(file):
#     file_url = url_for('static', filename=f'uploads/{file}')
#     return f'The URL for the file is: {file_url}'

@app.route('/user/any', methods=['PATCH'])
def update_any_user():
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = Inv_User.getUserById(user_id)
        user_email = user_data['email'] or None
        # Extracting the fields to be updated from the request data
        update_fields = {key: value for key, value in data.items()}
        # update_fields = {key: value for key, value in data.items() if key in ['first_name', 'last_name', 'other_name', 'email','dob', 'address', 'country', 'city', 'street_name', 'lon', 'lat' ]}
        post_data = Inv_User.update_user_any(user_id, user_email, **update_fields)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'user_id': user_id,
                    'updated_by_id': user_email,
                    'updated_by': user_email
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')

@app.route('/user', methods=['GET'])
def update_any_user_get():
    msg = {}
    count_stats = None
    user_id = return_user_id(request)
    try:
        match = Inv_User.getUserById(user_id)
        if match != None and match != False:
            expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
            token = jwt.encode({'exp': expiration_date, 'id': match['id']}, app.config['SECRET_KEY'], algorithm='HS256')
            if match['role'] == 'STUDENT':
                count_stats = {
                    "file": Inv_Fileupload.countFileById(match['id'])
                }
            msg = { "user": match | {"count_stats": count_stats} }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        else:
            invalidUserOjectErrorMsg= {"code": 404, "User unavailable": 'Failed'}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=404, mimetype='application/json')
    except Exception as e:
            invalidUserOjectErrorMsg= {"code": 500, "message": 'Failed', "error": str(e)}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=500, mimetype='application/json')


@app.route('/upload', methods=['POST', 'PATCH'])
@token_required
def upload():
    token = request.headers.get('Authorization')
    token = token.split(" ")[1]        
    token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
    # data = request.get_json()
    user_id = token_data['id'] or None
    user_data = Inv_User.getUserById(user_id)
    user_email = user_data['email'] or None

    msg = {
        "code": 403,
        "message": 'Failed',
    }
    if request.method in ['POST', 'PATCH']:
        data_source = fileUploadManager(request, user_id, user_email)
        if data_source['status']:
            msg = {
                "code": 200,
                "message": 'Successful',
                "other": data_source
            }
            return Response( json.dumps(msg), status=200, mimetype='application/json')
        
        msg = {
            "code": 500,
            "message": 'Failed',
            "other": data_source
        }
        return Response( json.dumps(msg), status=200, mimetype='application/json')


@app.route('/upload/<string:id>', methods=['PATCH', 'GET'])
@token_required
def uploadUpdate(id):
    if request.method == 'GET':
        return Inv_Fileupload.getFileById(id)
    if request.method == 'PATCH':
        return fileUploadManager(request, id)
    msg = {
        "code": 404,
        "message": 'Failed',
    }
    return Response( json.dumps(msg), status=404, mimetype='application/json')

@app.route('/file/delete/<string:id>', methods=['DELETE'])
@token_required
def fileDelete(id):
    msg = {
        "code": 403,
        "message": 'Failed',
    }
    if request.method == 'DELETE':
        if Inv_Fileupload.delete_file(id):
            msg = {
                "code": 200,
                "message": 'Successful',
            }
            return Response( json.dumps(msg), status=200, mimetype='application/json')
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg = {
            "code": 404,
            "message": 'Failed',
        }
        return Response( json.dumps(msg), status=404, mimetype='application/json')


@app.route('/usage-paging', methods=['GET'])
@token_required
def usageByStudentLastTen():
    # print(request.headers.getlist("X-Forwarded-For"))
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    # Extract query parameters
    page = request.args.get('page', default=1, type=int)
    search = request.args.get('search')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    per_page = request.args.get('per_page', default=10, type=int)
    count_stats = None
    if request.method == 'GET':
        try:
            request_data = Inv_Usage.getAllUsage(search, page, per_page, status, start_date, end_date)
            user_id = return_user_id(request)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data['data'],
                "pagination": request_data['pagination'],
                'previous': request_data['previous'],
                'next': request_data['next'],
                "count_stats": count_stats
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5003)

