from flask import Flask, g, request, jsonify, escape
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

report_api = Blueprint('report_api', __name__)

@report_api.route('/art/<int:artID>',methods=["POST"], strict_slashes=False)
def reportArt(artID):
    return "Not implemeted"

@report_api.route('/tag/<int:tagID>',methods=["POST"], strict_slashes=False)
def reportTag(tagID):
    return "Not implemeted"

@report_api.route('/user/<int:userID>',methods=["POST"], strict_slashes=False)
def reportUser(userID):
    return "Not implemeted"