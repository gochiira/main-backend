from flask import Flask, g, request, jsonify, escape
from flask_httpauth import HTTPTokenAuth

auth = HTTPTokenAuth('dummy_key')
scrape_api = Blueprint('scrape_api', __name__)

@scrape_api.route('/twitter/',methods=["POST"], strict_slashes=False)
def addArtByTwitter():
    return "Not implemeted"
    
@scrape_api.route('/pixiv/',methods=["POST"], strict_slashes=False)
def addArtByPixiv():
    return "Not implemeted"