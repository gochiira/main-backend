from flask import Blueprint, g, request, jsonify, escape
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest
from werkzeug.utils import secure_filename
from datetime import datetime

arts_api = Blueprint('arts_api', __name__)

#
# イラストの投稿関連
#

ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg"]

def isNotAllowedFile(filename):
    if filename == "":
        return True
    if '.' not in filename:
        return True
    if filename.rsplit('.', 1)[1].lower()\
    in ALLOWED_EXTENSIONS:
        return True
    return False

# だいたい完成! (複数画像未サポート 画像重複確認未サポート 複数解像度作成未サポート)
@arts_api.route('/',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createArt():
    params = request.get_json()
    '''
    画像複数対応は面倒くさいのでとりあえずなしにしましょう
    
    REQ
    {
        "title":"Test",
        "caption":"テストデータ",
        "originUrl": "元URL",
        "originService": "元サービス名",
        "artist":{
            //どれか1つが存在するかつあってればOK
            "twitterID":"適当でも",
            "pixivID":"適当でも",
            "name":"適当でも"
        },
        "tag":["","",""]
    }
    '''
    #パラメータ確認
    requiredParams = set(
        "title",
        "originUrl"
    )
    validParams = [
        "title",
        "caption",
        "originUrl",
        "originService",
        "artist",
        "tag"
    ]
    #必須パラメータ確認
    params = {p:params[p] for p in params.keys() if p in validParams}
    if not requiredParams.issubset(params.keys())\
    or "file" not in request.files:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    #作者パラメータ確認
    if "name" not in params["artist"]\
    and "twitterID" not in params["artist"]\
    and "pixivsID" not in params["artist"]:
        return jsonify(status=400, message="Artist paramators are invalid.")
    # タイトル重複確認
    if g.db.has(
        "illust_main",
        "illustName=?",
        (params["title"],)
    ):
        return jsonify(status=409, message="The art named %s is already exist"%(params["title"]))
    #ファイルパラメータ確認
    file = request.files['file']
    filename = file.filename
    if isNotAllowedFile(filename):
        return jsonify(status=400, message="Specified image is invalid.")
    #TODO:　ここで画像重複確認処理を挟む
    #作者情報取得
    artistName = params["artist"].get("name", None)
    pixivID = params["artist"].get("pixivID", None)
    twitterID = params["artist"].get("twitterID", None)
    #既存の作者でなければ新規作成
    if not g.db.has(
        "info_artist",
        "artistName=? OR pixivID=? OR twitterID=?",
        (artistName,pixivID,twitterID)
    ):
        resp = g.db.edit(
            "INSERT INTO info_artist (artistName,twitterID,pixivID) VALUES (?,?,?)",
            (artistName,pixivID,twitterID)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    #作者IDを取得する
    artistID = g.db.get(
        "SELECT artistID FROM info_artist WHERE artistName=? OR pixivID=? or twitterID=?",
        (artistName,pixivID,twitterID)
    )
    #作品情報取得
    illustName = params.get("title")
    illustDescription = params.get("caption", None)
    illustDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    illustPage = params.get("pages", 1)
    illustOriginUrl = params.get("originUrl", None)
    illustOriginSite = params.get("originService", "独自")
    #データ登録
    resp = g.db.edit(
        "INSERT INTO illust_main (artistID,illustName,illustDescription,illustDate,illustPage,illustLike,illustOriginUrl,illustOriginSite,userID) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            artistID,
            illustName,
            illustDescription,
            illustDate,
            illustPage,
            0,
            illustOriginUrl,
            illustOriginSite,
            g.userID
        )
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # 登録した画像のIDを取得
    illustID = g.db.get("SELECT illustID FROM illust_main WHERE illustName=?", illustName)[0][0]
    #画像保存
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    #タグ情報取得/作成
    for t in params["tag"]:
        if not g.db.has("info_tag","tagName=?", (t,)):
            g.db.edit("INSERT INTO info_tag (tagName) VALUES (?)", (t,))
        tagID = g.db.get("SELECT tagID FROM info_tag WHERE tagName=?",(t,))
        resp = g.db.edit("INSERT INTO illust_tag (illustID,tagID) VALUES (?,?)",(illustID,tagID))
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=201, message="Created", illustID=illustID)

@arts_api.route('/<int:illustID>',methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def destroyArt(illustID):
    params = request.get_json()
    return jsonify(status=404, message="NotImplemented")

@arts_api.route('/<int:illustID>',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArt(illustID):
    artData = g.db.get(
        "SELECT * FROM illust_main INNER JOIN info_artist ON illust_main.artistID = info_artist.artistID WHERE illustID = ?",
        (illustID,)
    )
    if not len(artData):
        return jsonify(status=404, message="The art data was not found.")
    artData = artData[0]
    #タグ情報取得
    tagData = g.db.get(
        "SELECT tagID,tagName,nsfw FROM illust_tag natural join info_tag WHERE illustID = ?",
        (illustID,)
    )
    #キャラ情報取得
    charaData = g.db.get(
        "SELECT charaID,charaName FROM illust_chara natural join info_chara WHERE illustID = ?",
        (illustID,)
    )
    return jsonify(status=200, data={
        "illustID": artData[0],
        "userID": artData[1],
        "title": artData[3],
        "caption": artData[4],
        "date": artData[5],
        "pages": artData[6],
        "like": artData[7],
        "originUrl": artData[8],
        "originService": artData[9],
        "nsfw": artData[10],
        "artist": {
            "id": artData[2],
            "name": artData[13],
            "icon": artData[15],
        },
        "tag": [[t[0],t[1],t[2]] for t in tagData],
        "chara": [[c[0],c[1]] for c in charaData]
    })
    
@arts_api.route('/<int:illustID>',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editArt(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    validParams = [
        "artistID",
        "illustName",
        "illustDescription",
        "illustDate",
        "illustPage",
        "illustLike",
        "illustOriginUrl",
        "illustOriginSite",
        "userID"
    ]
    params = {p:params[p] for p in params.keys() if p in validParams}
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "artistID" in params.keys():
        isExist = g.db.has("info_artist","artistID=?",(params[p],))
        if not isExist:
            return jsonify(status=400, message="Specified artist was not found.")
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `illust_main` SET `%s`=? WHERE illustID=?"%(p),
            (params[p],illustID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")
    
#
# イラストのタグ関連
#   createArtTag は createArtと同時にされるので無い

@arts_api.route('/<int:illustID>/tags',methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteArtTag(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        tagID = int(params.get("tagID"))
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has("illust_tag","illustID=? AND tagID=?",(illustID,tagID,))
    if not isExist:
        return jsonify(status=400, message="The tag is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `illust_tag` "\
        + "WHERE illustID = ? AND tagID = ?",
        (illustID,tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")
    
@arts_api.route('/<int:illustID>/tags',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtTag(illustID):
    '''指定されたイラスト付属のタグ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        "SELECT * FROM info_tag "\
        + "NATURAL JOIN (SELECT tagID FROM illust_tag WHERE illustID=?)",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any tag.")
    return jsonify(
        status=200,
        message="found",
        data = [{
            "tagID": r[0],
            "name": r[1],
            "caption": r[2],
            "nsfw": r[3],
            "endpoint": r[4]
        } for r in resp]
    )
    
@arts_api.route('/<int:illustID>/tags',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtTag(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        charaID = int(params.get("tagID"))
        isExist = g.db.has("info_tag","tagID=?",(tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has("illust_tag","illustID=? AND tagID=?",(illustID,tagID,))
    if isExist:
        return jsonify(status=400, message="The tag is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `illust_tag` (`illustID`,`charaID`) "\
        + "VALUES (?,?);",
        (illustID,tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")
    
#
# イラストのキャラ関連
#   createArtCharacater は createArtと同時にされるので無い

@arts_api.route('/<int:illustID>/characters',methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteArtCharacter(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        charaID = int(params.get("charaID"))
    except:
        return jsonify(status=400, message="charaID is invalid, or not specified.")
    isExist = g.db.has("illust_chara","illustID=? AND charaID=?",(illustID,charaID,))
    if not isExist:
        return jsonify(status=400, message="The character is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `illust_chara` "\
        + "WHERE illustID = ? AND charaID = ?",
        (illustID,charaID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")
    
@arts_api.route('/<int:illustID>/characters',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtCharacter(illustID):
    '''指定されたイラスト付属のキャラ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        "SELECT * FROM info_chara "\
        + "NATURAL JOIN (SELECT charaID FROM illust_chara WHERE illustID=?)",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any character.")
    return jsonify(
        status=200,
        message="found",
        data = [{
            "charaID": r[0],
            "name": r[1],
            "caption": r[2],
            "background": r[3],
            "icon": r[4],
            "birthday": r[5],
            "endpoint": r[6]
        } for r in resp]
    )
    
@arts_api.route('/<int:illustID>/characters',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtCharacter(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        charaID = int(params.get("charaID"))
        isExist = g.db.has("info_chara","charaID=?",(charaID,))
        if charaID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="charaID is invalid, or not specified.")
    isExist = g.db.has("illust_chara","illustID=? AND charaID=?",(illustID,charaID,))
    if isExist:
        return jsonify(status=400, message="The character is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `illust_chara` (`illustID`,`charaID`) "\
        + "VALUES (?,?);",
        (illustID,charaID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")
    
#
# イラストのいいね関連
#   無限にいいねできるものとする

@arts_api.route('/<int:illustID>/likes',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtLike(illustID):
    resp = g.db.edit(
        "UPDATE illust_main SET illustLike = illustLike + 1 WHERE illustID = ?",
        (illustID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    resp2 = g.db.get(
        "SELECT illustLike FROM illust_main WHERE illustID = ?",
        (illustID,)
    )
    return jsonify(status=200, message="Update succeed.", likes=resp2[0][0])
