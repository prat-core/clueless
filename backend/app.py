import flask
import flask_cors
import os
import requests
from flask import request, jsonify
import speech_recognition as sr
import tempfile
import base64
from flask_socketio import SocketIO, emit

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Wispr Flow API configuration
WISPR_API_KEY = os.getenv('WISPR_API_KEY', '')
WISPR_API_URL = "https://api.wisprflow.ai/v1"

# flask API routes
@app.route('/user_text_input', methods=['POST'])
def user_text_input():
    """
    Handle text input from user.
    Expects JSON payload with 'text' field.
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        user_text = data['text']
        
        # Process the text input here
        # For now, just return the received text
        response = {
            'message': 'Text input received successfully',
            'user_input': user_text,
            'status': 'success'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing text input: {str(e)}'}), 500

# wispr integration
@app.route('/user_speech_input', methods=['POST'])
def user_speech_input():
    try:
        # check if we have wispr api key
        if not WISPR_API_KEY:
            # fallback to google speech recognition if no wispr api key
            return process_speech_fallback()
        
        # try to get audio data from different sources
        audio_data = None
        audio_format = None
        
        # method 1: check for audio file upload
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file.filename != '':
                audio_data = audio_file.read()
                audio_format = audio_file.content_type or 'audio/wav'
        
        # method 2: check for base64 encoded audio in JSON
        elif request.is_json:
            data = request.get_json()
            if 'audio_data' in data:
                audio_data = base64.b64decode(data['audio_data'])
                audio_format = data.get('audio_format', 'audio/wav')
        
        if not audio_data:
            return jsonify({'error': 'No audio data provided'}), 400
        
        # process with wispr flow api
        return process_with_wispr(audio_data, audio_format)
        
    except Exception as e:
        return jsonify({'error': f'Error processing speech input: {str(e)}'}), 500

def process_with_wispr(audio_data, audio_format):
    try:
        # prepare audio data for wispr api
        if isinstance(audio_data, bytes):
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        else:
            audio_base64 = audio_data
        
        # wispr api request
        headers = {
            'Authorization': f'Bearer {WISPR_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'audio': audio_base64,
            'format': audio_format,
            'stream': False
        }
        
        response = requests.post(
            f"{WISPR_API_URL}/transcribe",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            transcribed_text = result.get('text', '')
            
            return jsonify({
                'message': 'Speech processed successfully with Wispr Flow',
                'user_input': transcribed_text,
                'status': 'success',
                'provider': 'wispr_flow'
            }), 200
        else:
            return jsonify({
                'error': f'Wispr API error: {response.status_code} - {response.text}'
            }), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'Error with Wispr API: {str(e)}'}), 500

def process_speech_fallback():
    try:
        # check if audio file is present
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            
            try:
                # use speech recognition to convert speech to text
                with sr.AudioFile(temp_file.name) as source:
                    # adjust for ambient noise
                    recognizer.adjust_for_ambient_noise(source)
                    # record the audio
                    audio_data = recognizer.record(source)
                    
                    # recognize speech using google's service
                    user_speech_text = recognizer.recognize_google(audio_data)
                
                # Process the speech input here
                response = {
                    'message': 'Speech input processed successfully (fallback)',
                    'user_input': user_speech_text,
                    'status': 'success',
                    'provider': 'google_speech'
                }
                
                return jsonify(response), 200
                
            except sr.UnknownValueError:
                return jsonify({'error': 'Speech recognition could not understand the audio'}), 400
            except sr.RequestError as e:
                return jsonify({'error': f'Speech recognition service error: {str(e)}'}), 500
            finally:
                # clean up temporary file
                os.unlink(temp_file.name)
                
    except Exception as e:
        return jsonify({'error': f'Error processing speech input: {str(e)}'}), 500

@app.route('/wispr_config', methods=['GET'])
def get_wispr_config():
    return jsonify({
        'wispr_enabled': bool(WISPR_API_KEY),
        'api_url': WISPR_API_URL,
        'fallback_available': True
    })

# just to check if the flask server is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
