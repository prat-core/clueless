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
        current_url = data.get('current_url', None)  # Current page URL from frontend
        
        if not AI_AVAILABLE:
            return jsonify({
                'error': 'AI processor not available. Please check your configuration.',
                'status': 'error'
            }), 503
        
        # Process the query with proper tool calling (navigation vs RAG)
        result = ai_processor.route_query(user_message, current_url=current_url)
        
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

@app.route('/get-html-elements', methods=['POST'])
def get_html_elements():
    """
    New endpoint to convert navigation path to HTML elements for startGuide function
    """
    try:
        data = request.get_json()
        if not data or 'user_query' not in data:
            return jsonify({'error': 'No user_query provided'}), 400
        
        user_query = data['user_query']
        start_location = data.get('start_location', None)
        
        if not AGENT_AVAILABLE:
            return jsonify({
                'error': 'Navigation agent not available. Please check your configuration.',
                'status': 'error'
            }), 503
        
        # Get the navigation path using existing navigation agent
        from ai.navigation_tool import create_navigation_tool, convert_nodes_to_html_list
        from ai.neo4j_processor import neo4j_processor
        
        # Create navigation tool and get path
        nav_tool = create_navigation_tool()
        if not nav_tool:
            return jsonify({
                'error': 'Failed to create navigation tool',
                'status': 'error'
            }), 503
        
        # Process navigation query to get the path
        nav_result = nav_tool.process_navigation_query(user_query, start_location)
        
        if nav_result['status'] != 'success':
            return jsonify({
                'error': nav_result.get('message', 'Navigation failed'),
                'status': 'error',
                'details': nav_result
            }), 400
        
        # Extract the raw path nodes and convert to HTML
        navigation_path = nav_result.get('navigation_path', [])
        if not navigation_path:
            return jsonify({
                'error': 'No navigation path found',
                'status': 'error'
            }), 400
        
        # Extract raw node data from navigation steps
        raw_nodes = []
        for step in navigation_path:
            if 'node_data' in step:
                raw_nodes.append(step['node_data'])
        
        # Convert nodes to HTML elements
        html_elements = convert_nodes_to_html_list(raw_nodes)
        
        # Close navigation tool
        nav_tool.close()
        
        return jsonify({
            'status': 'success',
            'html_elements': html_elements,
            'step_count': len(html_elements),
            'user_query': user_query,
            'navigation_response': nav_result.get('response', ''),
            'timestamp': nav_result.get('timestamp')
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error processing HTML elements request: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)

    app.run(debug=True, host='0.0.0.0', port=5000)