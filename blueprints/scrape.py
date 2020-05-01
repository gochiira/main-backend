from flask import Blueprint, g, request, jsonify, escape, current_app
from flask_httpauth import HTTPTokenAuth
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
from .lib.pixiv_client import IllustGetter
from .lib.twitter_client import TweetGetter
from .lib.convertImages import *
# from werkzeug.utils import secure_filename
from tempfile import TemporaryDirectory
from base64 import b64encode
from uuid import uuid4
import os.path
import shutil
from imghdr import what as what_img

CDN_ADDRESS = "http://192.168.0.3:5000/static/temp/"
ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg", "webp"]


def isNotAllowedFile(filename):
    if filename == ""\
        or '.' not in filename\
        or (filename.rsplit('.', 1)[1].lower()
            not in ALLOWED_EXTENSIONS):
        return True
    return False


scrape_api = Blueprint('scrape_api', __name__)


@scrape_api.route('/twitter', methods=["POST"], strict_slashes=False)
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


@scrape_api.route('/pixiv', methods=["POST"], strict_slashes=False)
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
    for i, img in enumerate(resp["illust"]["imgs"]):
        filename = os.path.basename(img['thumb_src'])
        if not os.path.isfile('static/temp/'+filename):
            filePath = os.path.join(
                current_app.config['TEMP_FOLDER'],
                filename
            )
            ig.downloadIllust(img['thumb_src'], filePath)
        resp["illust"]["imgs"][i]['thumb_src'] = CDN_ADDRESS + filename
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/self', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtBySelf():
    # これだけアップロードか何か、エンドポイント変えたほうがいいような気がする...
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        # 大丈夫そうなので保存
        filePath = os.path.join(
            current_app.config['TEMP_FOLDER'],
            uniqueID + ".raw"
        )
        shutil.copy2(tempPath, filePath)
    return jsonify(
        status=200,
        message="ok",
        data={
            "url": CDN_ADDRESS + uniqueID + ".raw"
        }
    )


@scrape_api.route('/predict_tag', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def predictTag():
    return "Not implemeted"
