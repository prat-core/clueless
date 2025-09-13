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
    from ai.neo4j_processor import neo4j_processor
    kg = neo4j_processor()
    NEO4J_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Neo4j not available: {e}")
    kg = None
    NEO4J_AVAILABLE = False

# Initialize RAG processor
try:
    from ai.rag_process import rag_processor
    RAG_AVAILABLE = True
    print("✅ RAG processor initialized successfully")
except Exception as e:
    print(f"⚠️  RAG processor not available: {e}")
    rag_processor = None
    RAG_AVAILABLE = False


# flask API routes
@app.route('/chat', methods=['POST'])
def chat_with_claude():
    """
    New endpoint for Claude-powered chat with RAG processing
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
        
        user_message = data['message']
        use_retrieval = data.get('use_retrieval', True)  # Optional parameter
        
        if not RAG_AVAILABLE:
            return jsonify({
                'error': 'RAG processor not available. Please check your configuration.',
                'status': 'error'
            }), 503
        
        # Process the query with RAG
        result = rag_processor.process_query(user_message, use_retrieval=use_retrieval)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error processing chat request: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/user_text_input', methods=['POST'])
def user_text_input():
    """
    Original endpoint - now enhanced with optional Claude processing
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        user_text = data['text']
        use_claude = data.get('use_claude', False)  # Optional Claude processing
        
        response = {
            'message': 'Text input received successfully',
            'user_input': user_text,
            'status': 'success'
        }
        
        # Optional Claude processing
        if use_claude and RAG_AVAILABLE:
            claude_result = rag_processor.process_query(user_text, use_retrieval=False)
            response['claude_response'] = claude_result.get('response')
            response['claude_status'] = claude_result.get('status')
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing text input: {str(e)}'}), 500

# just to check if the flask server is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
