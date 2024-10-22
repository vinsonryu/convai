from datetime import datetime
import gtts
import speech_recognition as sr
from flask import Flask, flash, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename
from google.cloud import texttospeech
from google.cloud import storage
import os
from google.cloud import speech
from google.cloud import language_v1
import io
# Set up Google Cloud Storage bucket information
GCS_BUCKET_NAME = " uploads_123"

# Initialize the Google Cloud Storage client
lang_client = language_v1.LanguageServiceClient()
client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()
app = Flask(__name__)
app.secret_key = 'kirakira'
# Configure upload folder
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav','txt','mp3'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files(loc):
    files = []
    for filename in os.listdir(loc):
        if allowed_file(filename):
            files.append(filename)
            print(filename)
    files.sort(reverse=True)
    return files

        
def transcribe_file(audio_file: str) -> speech.RecognizeResponse:
    client = speech.SpeechClient()

    with open(audio_file, "rb") as f:
        audio_content = f.read()

    audio = speech.RecognitionAudio(content=audio_content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,  
        sample_rate_hertz=24000,
        language_code="en-US",
    )

    response = client.recognize(config=config, audio=audio)

  
    for result in response.results:
        print(f"Transcript: {result.alternatives[0].transcript}")
    if response.results:
        return response.results.pop().alternatives.pop().transcript
            
    return response

@app.route('/tts/<filename>')
def get_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename, mimetype='audio/mpeg')
files = get_files(UPLOAD_FOLDER)
audios = get_files(AUDIO_FOLDER)
@app.route('/')
def index():
    files = get_files(UPLOAD_FOLDER)
    audios = get_files(AUDIO_FOLDER)
    return render_template('index.html', files=files, audios=audios)

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
        # filename = secure_filename(file.filename)
        filename = "audio"+datetime.now().strftime("%Y%m%d-%I%M%S") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash('File uploaded successfully')

        # Load audio file (make sure the path to your file is correct)
        audio_file_path = file_path
        file_root, file_extension = os.path.splitext(file_path)

        result = transcribe_file(audio_file_path)
        
        document = language_v1.types.Document(
        content=result, type_=language_v1.types.Document.Type.PLAIN_TEXT)

        # Detects the sentiment of the text
        sentiment = lang_client.analyze_sentiment(
            request={"document": document}
        ).document_sentiment
        if sentiment.score>0:
            sen = "positive"
        else:
            sen = "negative"
        sentiment_result = f"Sentiment analysis,, sentiment: {sen} magnitude: {sentiment.magnitude}, score: {sentiment.score}"
        print(sentiment_result)
        # Save transcript to a text file
        result+=sentiment_result
        text_file = file_root + ".txt"
        with open(text_file, "w") as file:
            file.write(result)
        files = get_files(UPLOAD_FOLDER)
        audios = get_files(AUDIO_FOLDER)
        
    return render_template('index.html', transcription=result, bomb="boodies",sentiment_analysis=sentiment_result, files=files, audios=audios)


@app.route('/uploads/<filename>')
def view_file(filename):
    # Serve the text file for viewing
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



    
@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)
    
    # Perform Text-to-Speech conversion
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    # Sentiment Analysis
    document = language_v1.types.Document(
        content=text, type_=language_v1.types.Document.Type.PLAIN_TEXT
    )

    # Detects the sentiment of the text
    sentiment = lang_client.analyze_sentiment(
        request={"document": document}
    ).document_sentiment
    if sentiment.score>0:
        sen = "positive"
    else:
        sen = "negative"
    # Generate sentiment analysis output
    sentiment_result = f"Sentiment analysis, sentiment: {sen} ,magnitude: {sentiment.magnitude}, score: {sentiment.score}"
    print(sentiment_result)
    
    # Save the synthesized speech as an audio file
    output_filename = "output_" + datetime.now().strftime("%Y%m%d-%I%M%S") + ".mp3"
    output_filepath = os.path.join(app.config['AUDIO_FOLDER'], output_filename)
    with open(output_filepath, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_filepath}"')

    # Pass the text, sentiment, and audio file to the frontend
    audios = get_files(app.config['AUDIO_FOLDER'])
    
    return render_template('index.html', transcription=text, sentiment_analysis=sentiment_result, audios=audios, files=files)


@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
