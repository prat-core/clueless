import flask
import flask_cors
import os
import requests
from datetime import datetime
from flask import request, jsonify
from flask_socketio import SocketIO

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

try:
    from ai.neo4j_processor import neo4j_processor
    kg = neo4j_processor()
    NEO4J_AVAILABLE = True
    from ai.smart_navigation_agent import SmartNavigationAgent
    navigation_agent = SmartNavigationAgent()
    AGENT_AVAILABLE = True
    print("✅ Smart Navigation Agent available")
except Exception as e:
    print(f"⚠️  Smart Navigation Agent not available: {e}")
    navigation_agent = None
    AGENT_AVAILABLE = False

# Initialize AI processor with tool calling
try:
    from ai.general_llm import QueryRouter
    ai_processor = QueryRouter()
    AI_AVAILABLE = ai_processor is not None
    if AI_AVAILABLE:
        print("✅ AI processor with tool calling initialized successfully")
    else:
        print("⚠️  AI processor initialization failed - check environment variables")
except Exception as e:
    print(f"⚠️  AI processor not available: {e}")
    ai_processor = None
    AI_AVAILABLE = False


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
        
        if not AI_AVAILABLE:
            return jsonify({
                'error': 'AI processor not available. Please check your configuration.',
                'status': 'error'
            }), 503
        
        # Process the query with proper tool calling (navigation vs RAG)
        result = ai_processor.route_query(user_message)
        
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
        
        if AGENT_AVAILABLE:
            result = navigation_agent.process_user_input(user_text)
            response = {
                'message': result['message'],
                'user_input': result['user_input'],
                'is_navigation_prompt': result['is_navigation_prompt'],
                'claude_confidence': result['claude_confidence'],
                'claude_reasoning': result['claude_reasoning'],
                'end_node': result['end_node'],
                'semantic_confidence': result['semantic_confidence'],
                'status': 'success'
            }
        else:
            response = {
                'message': 'Text input received successfully (Smart Navigation Agent unavailable)',
                'user_input': user_text,
                'status': 'success'
            }
        
        # Optional AI processing
        if use_claude and AI_AVAILABLE:
            ai_result = ai_processor.route_query(user_text)
            response['ai_response'] = ai_result.get('response')
            response['ai_status'] = ai_result.get('status')
            response['tool_used'] = ai_result.get('tool_used', 'unknown')
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing text input: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)

    app.run(debug=True, host='0.0.0.0', port=5000)