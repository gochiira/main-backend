from flask import Blueprint, g, request, jsonify, escape, current_app
from flask_httpauth import HTTPTokenAuth
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest
from .lib.pixiv_client import IllustGetter
from .lib.twitter_client import TweetGetter
import os.path

scrape_api = Blueprint('scrape_api', __name__)

@scrape_api.route('/twitter',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtByTwitter():
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    tg = TweetGetter()
    resp = tg.getTweet(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    return jsonify(status='200', message='ok', data=resp)
        
    
@scrape_api.route('/pixiv',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtByPixiv():
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    ig = IllustGetter()
    resp = ig.getIllust(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    for i,img in enumerate(resp["illust"]["imgs"]):
        filename = os.path.basename(img['thumb_src'])
        if not os.path.isfile('static/temp/'+filename):
            ig.downloadIllust(img['thumb_src'], 'static/temp')
        resp["illust"]["imgs"][i]['thumb_src'] = 'http://localhost:5000/static/temp/' + filename
    return jsonify(status='200', message='ok', data=resp)

@scrape_api.route('/upload',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtBySelf():
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    return "200"

@scrape_api.route('/predict_tag',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def predictTag():
    return "Not implemeted"