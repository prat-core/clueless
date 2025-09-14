from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

try:
    from backend.ai.semantic_search import SimpleSemanticSearch
    semantic_search = SimpleSemanticSearch()
    SEMANTIC_AVAILABLE = True
    print("✅ Semantic search available")
except Exception as e:
    print(f"⚠️  Semantic search not available: {e}")
    semantic_search = None
    SEMANTIC_AVAILABLE = False

@app.route('/user_text_input', methods=['POST'])
def user_text_input():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        user_text = data['text']
        
        if SEMANTIC_AVAILABLE:
            search_result = semantic_search.find_end_node(user_text)
            response = {
                'message': 'Text input processed with semantic search',
                'user_input': user_text,
                'end_node': search_result['end_node'],
                'confidence': search_result['confidence'],
                'search_message': search_result['message'],
                'status': 'success'
            }
        else:
            response = {
                'message': 'Text input received successfully (semantic search unavailable)',
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