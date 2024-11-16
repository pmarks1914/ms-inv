import mimetypes
from Model import Fileupload
import os
import boto3
from dotenv import dotenv_values
from azure.storage.blob import BlobServiceClient, ContentSettings


get_env = dotenv_values(".env")  
# Initialize a session using your access keys
s3 = boto3.client(
    's3',
    aws_access_key_id=get_env['AWS_ACCESS_KEY_ID']  ,
    aws_secret_access_key=get_env['AWS_SECRET_ACCESS_KEY']  ,
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
            if str(request.form.get('type')) == "1":
                doc_type = "Certificate"
                slug = request.form.get('slug')
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "2":
                doc_type = "Transcript"
                slug = request.form.get('slug')
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "3":
                doc_type = "Identification Document"
                slug = request.form.get('slug')
                issued_date = request.form.get('issued_date')
                
            doc_format = file.content_type.split('/')[1]
            data_object = Fileupload.createFile(file.filename, file.filename, doc_type, doc_format, user_id, issued_date, slug)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object['id'] + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)

            # S3
            bucket_name = 'league-ms-s3'
            local_file_path = file_path
            s3_object_name = new_filename
            # Upload the file to S3
            try:
                s3.upload_file(local_file_path, bucket_name, s3_object_name, 
                ExtraArgs={
                    'ContentType': str(file_type),
                    'ContentDisposition': 'inline'
                } )
                azure_blob(new_filename, local_file_path, str(file_type))
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
            if str(request.form.get('type')) == "1":
                doc_type = "Certificate"
                slug = request.form.get('slug')
                issued_date = request.form.get('certificateDate')
            if str(request.form.get('type')) == "2":
                doc_type = "Transcript"
                slug = request.form.get('slug')
                issued_date = request.form.get('transcriptDate')
            if str(request.form.get('type')) == "3":
                doc_type = "Identification Document"
                slug = request.form.get('slug')
                issued_date = request.form.get('identificationDate')
            if str(request.form.get('type')) == "4":
                doc_type = "Evaluation Report"
                slug = "Report"
                issued_date = request.form.get('reportDate')
            if str(request.form.get('type')) == "5":
                doc_type = "Letter of Recommendation"
                slug = "Recommendation"
                issued_date = request.form.get('letterRecommendationDate')
            if str(request.form.get('type')) == "6":
                doc_type = "Evaluator Report"
                slug = "Evaluator Report"
                issued_date = request.form.get('evaluatorReportDate')
            doc_format = file.content_type.split('/')[1]
            data_object = Fileupload.createFile(file.filename, file.filename, doc_type, doc_format, user_id, issued_date, slug)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object['id'] + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)

            # S3
            bucket_name = 'league-ms-s3'
            local_file_path = file_path
            s3_object_name = new_filename
            # Upload the file to S3
            try:
                s3.upload_file(local_file_path, bucket_name, s3_object_name, 
                ExtraArgs={
                    'ContentType': str(file_type),
                    'ContentDisposition': 'inline'
                } )
                if str(request.form.get('type')) == "0":
                    # doc_type = "Photo"
                    pass
                if str(request.form.get('type')) == "1":
                    # doc_type = "Certificate"
                    new_data_object = {
                        'certificate': data_object['url'],
                        'certificateDate': issued_date,
                        'certificate_name': data_object['type'],
                        'certificate_id': data_object['id'],
                        'certificate_type': slug
                    }
                if str(request.form.get('type')) == "2":
                    # doc_type = "Transcript"
                    new_data_object = {
                        'transcript': data_object['url'],
                        'transcriptDate': issued_date,
                        'transcript_name': data_object['type'],
                        'transcript_id': data_object['id'],
                        'transcript_type': slug
                    }
                if str(request.form.get('type')) == "3":
                    # doc_type = "Identification Document"
                    new_data_object = {
                        'identification': data_object['url'],
                        'identificationDate': issued_date,
                        'identification_name': data_object['type'],
                        'identification_id': data_object['id'],
                        'identification_type': slug
                    }
                if str(request.form.get('type')) == "4":
                    # doc_type = "Evaluation Report"
                    new_data_object = {
                        'report': data_object['url'],
                        'reportDate': issued_date,
                        'report_id': data_object['id'],
                        'report_name': doc_type,
                        'report_type': slug
                    }
                if str(request.form.get('type')) == "5":
                    # doc_type = "Letter of Recommendation"
                    new_data_object = {
                        'recommendation': data_object['url'],
                        'letterRecommendationDate': issued_date,
                        'letterRecommendation_id': data_object['id'],
                        'letterRecommendation_name': doc_type,
                        'letterRecommendation_type': slug
                    }
                if str(request.form.get('type')) == "6":
                    # doc_type = "evaluator evaluayion report"
                    new_data_object = {
                        'evaluatorReport': data_object['url'],
                        'evaluatorReportDate': issued_date,
                        'evaluatorReport_id': data_object['id'],
                        'evaluatorReport_name': doc_type,
                        'evaluatorReport_type': slug
                    }
                # Evaluation.update_evaluation(evaluation_id, user_email, **new_data_object)
                os.remove(local_file_path)  # Clean up the local file after upload
                return {'message': 'File uploaded successfull', 'status': True}
            except Exception as e:
                return {'message': 'File uploaded failed.', 'status': False, 'error': str(e)}


    except Exception as e:
        return {'message': 'File uploading failed', 'status': False, 'error': str(e)}


def azure_blob(blob_name, file_path, file_type):
    # Set up your connection string and container name
    connection_string = get_env['AZURE_CONNECTION_STRING'] 
    container_name = get_env['AZURE_CONTAINER_NAME'] 
    # Create a BlobServiceClient object using the connection string
    try:
        # Create a BlobServiceClient object using the connection string
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        # Create a container client
        container_client = blob_service_client.get_container_client(container_name)
        # Check if the container exists
        if not container_client.exists():
            # container_client.create_container()
            print(f"Container '{container_name}' created successfully.")
        else:
            print(f"Container '{container_name}' already exists.")

        # Upload the blob
        with open(file_path, "rb") as data:            
            container_client.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            content_settings = ContentSettings(
                content_type=file_type,
                content_disposition="inline"
                )
            )

            # print(f"Blob '{blob_name}' uploaded to container '{container_name}' successfully.")

    except Exception as ex:
        print(f"An error occurred: {ex}")

