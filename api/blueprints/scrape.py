from flask import Blueprint, g, request, jsonify, current_app
from ..extensions import (
    auth, limiter, handleApiPermission, record
)
from ..scraper_lib.pixiv_client import IllustGetter
from ..scraper_lib.twitter_client import TweetGetter
from ..scraper_lib.seiga_client import SeigaGetter
from ..scraper_lib.booth_client import BoothGetter
from ..scraper_lib.danbooru_client import DanbooruGetter
from tempfile import TemporaryDirectory
from base64 import b64encode
from uuid import uuid4
import os.path
import shutil
from imghdr import what as what_img
from imghdr import tests
from os import environ
from dotenv import load_dotenv

# .env読み込み
load_dotenv(verbose=True, override=True)

CDN_ADDRESS = f"{environ.get('API_OWN_ADDRESS')}/static/temp/"
TWITTER_CONSUMER_KEY = environ.get('API_TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = environ.get('API_TWITTER_CONSUMER_SECRET')
TWITTER_AUTH_TOKEN = environ.get('API_TWITTER_AUTH_TOKEN')
TWITTER_AUTH_SECRET = environ.get('API_TWITTER_AUTH_SECRET')
PIXIV_AUTH = environ.get('API_PIXIV_FILE')
NICONICO_AUTH = environ.get('API_NICONICO_FILE')

ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg", "webp"]
JPEG_MARK = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06' \
    b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'


def test_jpeg(h, f):
    """JPEG data in JFIF format"""
    if b'JFIF' in h[:23]:
        return 'jpeg'
    """JPEG with small header"""
    if len(h) >= 32 and 67 == h[5] and h[:32] == JPEG_MARK:
        return 'jpeg'
    """JPEG data in JFIF or Exif format"""
    if h[6:10] in (b'JFIF', b'Exif') or h[:2] == b'\xff\xd8':
        return 'jpeg'


tests.append(test_jpeg)


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
@limiter.limit(handleApiPermission)
def getArtByTwitter():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    tg = TweetGetter(
        TWITTER_CONSUMER_KEY,
        TWITTER_CONSUMER_SECRET,
        TWITTER_AUTH_TOKEN,
        TWITTER_AUTH_SECRET
    )
    # 雑なエラー対応
    if params['url'].find("?") != -1:
        params['url'] = params['url'][:params['url'].find("?")]
    params['url'] = params['url'].replace("mobile.", "")
    resp = tg.getTweet(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/pixiv', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtByPixiv():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    ig = IllustGetter(PIXIV_AUTH)
    # 雑なエラー対応
    if params['url'].find("?") != -1:
        params['url'] = params['url'][:params["url"].find('?')]
    resp = ig.getIllust(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    for i, img in enumerate(resp["illust"]["imgs"]):
        fileName = os.path.basename(img['thumb_src'])
        if not os.path.isfile('static/temp/'+fileName):
            path = os.path.join('static/temp', fileName)
            ig.downloadIllust(img['thumb_src'], path=path)
        resp["illust"]["imgs"][i]['thumb_src'] = CDN_ADDRESS + fileName
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/seiga', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtByNicoNicoSeiga():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    sg = SeigaGetter(NICONICO_AUTH)
    # 雑なエラー対応
    if params['url'].find("?") != -1:
        params['url'] = params['url'][:params['url'].find("?")]
    resp = sg.getSeiga(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/danbooru', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtByDanbooru():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    sg = DanbooruGetter()
    # 雑なエラー対応
    if params['url'].find("?") != -1:
        params['url'] = params['url'][:params['url'].find("?")]
    resp = sg.getArt(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/booth', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtByBooth():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request')
    if 'url' not in params.keys():
        return jsonify(status='400', message='bad request')
    bg = BoothGetter()
    # 雑なエラー対応
    if params['url'].find("?") != -1:
        params['url'] = params['url'][:params['url'].find("?")]
    resp = bg.getProduct(params['url'])
    if resp == {}:
        return jsonify(status='400', message='bad request')
    return jsonify(status='200', message='ok', data=resp)


@scrape_api.route('/self', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtBySelf():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
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
            'static/temp',
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
@limiter.limit(handleApiPermission)
def predictTag():
    return "Not implemeted"
