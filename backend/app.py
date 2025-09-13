import flask
import flask_cors
import os
import requests
from flask import request, jsonify

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)

# webscraping function
@app.route('/webscrape', methods=['GET'])
def webscrape(url):
    continue

if __name__ == '__main__':
    app.run(debug=True)