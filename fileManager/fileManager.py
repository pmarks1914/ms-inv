import mimetypes
from Model import Inv_Fileupload
import os
import boto3
from dotenv import dotenv_values
from azure.storage.blob import BlobServiceClient, ContentSettings


get_env = dotenv_values(".env")  
# Initialize a session using your access keys
s3 = boto3.client(
    's3',
    aws_access_key_id=get_env['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=get_env['AWS_SECRET_ACCESS_KEY'],
    region_name=get_env['REGION_NAME']  
)
 
def fileUploadManager(request, user_id, user_email, *args):
    file = ""
    issued_date = ""
    slug = ''
    new_data_object = ''
    if 'photo' in request.files:     
        file = request.files['photo']
    elif 'cert' in request.files:
        file = request.files['cert']

    if file.filename == '':
        return {'message': 'No selected file', 'status': False}
    try:
        if request.method == 'POST':
            doc_type = ""
            # check types
            if str(request.form.get('type')) == "0":
                doc_type = "Photo"
                slug = doc_type
                issued_date = None
                
            doc_format = file.content_type.split('/')[1]
            data_object = Inv_Fileupload.createFile(file.filename, file.filename, doc_type, doc_format, user_id, issued_date, slug)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object['id'] + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)

            # S3
            bucket_name = get_env['AWS_BUCKET_NAME']
            local_file_path = file_path
            s3_object_name = new_filename
            # Upload the file to S3
            try:
                s3.upload_file(local_file_path, bucket_name, s3_object_name, 
                ExtraArgs={
                    'ContentType': str(file_type),
                    'ContentDisposition': 'inline'
                } )
                os.remove(local_file_path)  # Clean up the local file after upload
                return {'message': 'File uploaded successfull', 'status': True}
            except Exception as e:
                return {'message': 'File uploaded failed.', 'status': False, 'error': str(e)}

        if request.method == 'PATCH':
            doc_type = ""
            evaluation_id = None
            if request.form.get('evaluation_id'):
                evaluation_id = request.form.get('evaluation_id')

            if str(request.form.get('type')) == "0":
                doc_type = "Photo"
                slug = doc_type
                issued_date = None

            doc_format = file.content_type.split('/')[1]
            data_object = Inv_Fileupload.createFile(file.filename, file.filename, doc_type, doc_format, user_id, issued_date, slug)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object['id'] + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)

            # S3
            bucket_name = get_env['AWS_BUCKET_NAME']
            local_file_path = file_path
            s3_object_name = new_filename
            # Upload the file to S3
            try:
                s3.upload_file(local_file_path, bucket_name, s3_object_name, 
                ExtraArgs={
                    'ContentType': str(file_type),
                    'ContentDisposition': 'inline'
                } )
                # Evaluation.update_evaluation(evaluation_id, user_email, **new_data_object)
                os.remove(local_file_path)  # Clean up the local file after upload
                return {'message': 'File uploaded successfull', 'status': True}
            except Exception as e:
                return {'message': 'File uploaded failed.', 'status': False, 'error': str(e)}


    except Exception as e:
        return {'message': 'File uploading failed', 'status': False, 'error': str(e)}

