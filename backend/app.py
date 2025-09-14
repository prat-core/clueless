from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

try:
    from ai.smart_navigation_agent import SmartNavigationAgent
    navigation_agent = SmartNavigationAgent()
    AGENT_AVAILABLE = True
    print("✅ Smart Navigation Agent available")
except Exception as e:
    print(f"⚠️  Smart Navigation Agent not available: {e}")
    navigation_agent = None
    AGENT_AVAILABLE = False

@app.route('/user_text_input', methods=['POST'])
def user_text_input():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        user_text = data['text']
        
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
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing text input: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask API is running'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)