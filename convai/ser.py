from datetime import datetime
import gtts
import speech_recognition as sr
from flask import Flask, flash, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename
from google.cloud import texttospeech
from google.cloud import storage
client = texttospeech.TextToSpeechClient()
import os
from google.cloud import speech
import io
# Set up Google Cloud Storage bucket information
GCS_BUCKET_NAME = " uploads_123"

# Initialize the Google Cloud Storage client
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

@app.route('/tts/<filename>')
def get_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename, mimetype='audio/mpeg')

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
        print(file_path)

        # Load audio file (make sure the path to your file is correct)
        audio_file_path = file_path
        file_root, file_extension = os.path.splitext(file_path)
        print(f"audio file is :{audio_file_path}")
        
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
        result = transcribe_file(audio_file_path)
        flash(result)
        text_file = file_root + ".txt"
        with open(text_file, "w") as file:
            file.write(result)

        # Modify this block to call the speech to text API
        # Save transcript to same filename but .txt
        #
        #

    return render_template('index.html', transcription=result)

@app.route('/uploads/<filename>')
def view_file(filename):
    # Serve the text file for viewing
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



    
@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)
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

    # The response's audio_content is binary.
    with open("tts/output.mp3", "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')
    #
    # Modify this block to call the stext to speech API
    # Save the output as a audio file in the 'tts' directory 
    # Display the audio files at the bottom and allow the user to listen to them
    #

    return redirect('/') #success

@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)