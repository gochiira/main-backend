from flask import Blueprint, g, request, jsonify, escape, current_app
from flask_httpauth import HTTPTokenAuth
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

scrape_api = Blueprint('scrape_api', __name__)

@scrape_api.route('/twitter',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtByTwitter():
    return "Not implemeted"
    
@scrape_api.route('/pixiv',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtByPixiv():
    return "Not implemeted"