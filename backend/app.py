import flask
import flask_cors
import os
import requests
from flask import request, jsonify
from flask_socketio import SocketIO

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


try:
    from ai.neo4j_processor import SimpleNeo4jKG
    kg = SimpleNeo4jKG()
    NEO4J_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Neo4j not available: {e}")
    kg = None
    NEO4J_AVAILABLE = False


# flask API routes
@app.route('/user_text_input', methods=['POST'])
def user_text_input():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        user_text = data['text']
        
        response = {
            'message': 'Text input received successfully',
            'user_input': user_text,
            'status': 'success'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing text input: {str(e)}'}), 500

# just to check if the flask server is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
