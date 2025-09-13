import flask
import flask_cors
import os
import requests
from flask import request, jsonify

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)

# flask API routes
@app.route('/user_text_input', methods=['GET'])
def user_text_input():
    continue

def user_speech_input():
    continue

if __name__ == '__main__':
    app.run(debug=True)
