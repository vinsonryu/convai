from datetime import datetime
import json
from flask import Flask, flash, render_template, request, redirect, url_for, send_file, send_from_directory
from google.cloud import storage
import os
import io
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from dotenv import load_dotenv
load_dotenv()
google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Set up Google Cloud Storage bucket information
bucket_name = "uploads_123"

# Initialize the Google Cloud Storage client
storage_client = storage.Client()
app = Flask(__name__)
app.secret_key = 'kirakira'
project_id = 'convai-436601'
# Configure upload folder
ALLOWED_EXTENSIONS = {'wav','txt','mp3'}

vertexai.init(project=project_id, location="us-central1")

model = GenerativeModel("gemini-1.5-flash-001")
prompt = """
Please provide an exact trascript for the audio, followed by sentiment analysis.

Your response should follow the format:

Text: USERS SPEECH TRANSCRIPTION

Sentiment Analysis: positive|neutral|negative
"""

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


        
def transcribe_gcs(gcs_uri):
    audio_file = Part.from_uri(gcs_uri, mime_type="audio/wav")

    contents = [audio_file, prompt]

    response = model.generate_content(contents)
    return response.text



def get_cloud_files(bucket_name):
    files = []
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    for blob in blobs:
        files.append(blob.name)
    return files


def upload_blob(source_file_name, destination_blob_name):

    bucket_name = "uploads_123"
    try:
        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        generation_match_precondition = 0

        blob.upload_from_filename(
            source_file_name, 
            if_generation_match=generation_match_precondition
        )

        print(
            f"File {source_file_name} uploaded to {destination_blob_name} in bucket {bucket_name}."
        )
    except Exception as e:
        print(f"An error occurred while uploading the file: {e}")

def get_latest_files_from_gcs():
    """Retrieve the latest audio and text files from Google Cloud Storage."""
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs())

    audio_files = [blob for blob in blobs if blob.name.endswith('.wav') or blob.name.endswith('.mp3')]
    text_files = [blob for blob in blobs if blob.name.endswith('.txt')]

    audio_files.sort(key=lambda blob: blob.updated, reverse=True)
    text_files.sort(key=lambda blob: blob.updated, reverse=True)

    latest_audio = audio_files[0].name if audio_files else None
    latest_text = text_files[0].name if text_files else None
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(latest_audio)
    signed_url = blob.generate_signed_url(version="v4", expiration=3600)
    transcription = ""
    if latest_text:
        blob = bucket.blob(latest_text)
        transcription = blob.download_as_text()

    return signed_url, transcription

@app.route('/')
def default():
    files = get_cloud_files(bucket_name)
    latest_audio, transcription = get_latest_files_from_gcs()
    print(f"latest audio: {latest_audio}")
    return render_template('index.html',  files=files, latest_audio=latest_audio, transcription=transcription)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = "audio" + datetime.now().strftime("%Y%m%d-%I%M%S") + '.wav'
        
        bucket_name = "uploads_123"  
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        blob.upload_from_file(file, content_type=file.content_type)
        flash('File uploaded successfully to Cloud Storage')

        gcs_uri = f"gs://{bucket_name}/{filename}"  
        result = transcribe_gcs(gcs_uri)
        print(type(result))
    
        text_file_name = filename + ".txt"
        text_blob = bucket.blob(text_file_name)
        text_blob.upload_from_string(result, content_type="text/plain")
        
        files = get_cloud_files(bucket_name)
        
        return render_template('index.html', transcription=result, sentiment_analysis=result, files=files)

@app.route('/gcs/<filename>')
def serve_gcs_file(filename):
    """Generate a signed URL for a file in GCS."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        signed_url = blob.generate_signed_url(version="v4", expiration=3600)  
        print(f"Signed URL for {filename}: {signed_url}")  
        return signed_url
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        return str(e), 500



@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
