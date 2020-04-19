from flask import Blueprint, g, request, jsonify, escape, current_app
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest
from .lib.convertImages import *
from .lib.pixiv_client import IllustGetter
from .lib.twitter_client import TweetGetter
from datetime import datetime
import os
import tempfile
import json
import shutil
import traceback
import imagehash
from PIL import Image
from tempfile import TemporaryDirectory
from imghdr import what as what_img
from urllib.parse import parse_qs as parse_query

arts_api = Blueprint('arts_api', __name__)

#
# イラストの投稿関連
#


# だいたい完成! (複数画像未サポート 画像重複確認未サポート
@arts_api.route('/',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createArt():
    '''
    画像複数対応は面倒くさいのでとりあえずなしにしましょう
    
    REQ
    {
        "title":"Test",
        "caption":"テストデータ",
        "originUrl": "元URL",
        "originService": "元サービス名",
        "imageUrl": "画像の元URL",
        //どれか1つが存在するかつあってればOK
        "artist":{
            "twitterID":"適当でも",
            "pixivID":"適当でも",
            "name":"適当でも"
        },
        "tag":["","",""],
        "chara": ["","",""],
        "nsfw": 0
    }
    '''
    #最低限のパラメータ確認
    params = request.get_json()
    if not params:
        return jsonify(status='400', message='bad request: not json')
    #パラメータ確認
    requiredParams = set(("title","originService"))
    validParams = [
        "title",
        "caption",
        "imageUrl",
        "originUrl",
        "originService",
        "artist",
        "tag",
        "chara",
        "nsfw"
    ]
    #必須パラメータ確認
    #print(params.items())
    params = {p:params[p] for p in params.keys() if p in validParams}
    if not requiredParams.issubset(params.keys()):
        return jsonify(status='400', message='bad request: not enough')
    #作者パラメータ確認
    if "name" not in params["artist"]\
    and "twitterID" not in params["artist"]\
    and "pixivID" not in params["artist"]:
        return jsonify(status=400, message="Artist paramators are invalid.")
    #画像パラメータ確認
    if not any([
        params["imageUrl"].startswith("https://twitter.com/"),
        params["imageUrl"].startswith("https://www.pixiv.net/"),
        params["imageUrl"].startswith("https://cdn.gochiusa.team/temp/"),
        params["imageUrl"].startswith("http://192.168.0.3:5000/static/temp/")
    ]):
        return jsonify(status='400', message='bad request: not valid url')
    #作者情報取得
    artistName = params["artist"].get("name", None)
    pixivID = params["artist"].get("pixivID", None)
    twitterID = params["artist"].get("twitterID", None)
    #既存の作者でなければ新規作成
    if not g.db.has(
        "info_artist",
        "artistName=%s OR pixivID=%s OR twitterID=%s",
        (artistName,pixivID,twitterID)
    ):
        resp = g.db.edit(
            "INSERT INTO info_artist (artistName,twitterID,pixivID) VALUES (%s,%s,%s)",
            (artistName,pixivID,twitterID),
            False
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    #作者IDを取得する
    artistID = g.db.get(
        "SELECT artistID FROM info_artist WHERE artistName=%s OR pixivID=%s or twitterID=%s",
        (artistName,pixivID,twitterID)
    )[0][0]
    #作品情報取得
    illustName = params.get("title", "無題")
    illustDescription = params.get("caption", "コメントなし")
    illustDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #illustPage = params.get("pages", "1")
    illustPage = 1
    illustOriginUrl = params.get("originUrl", "https://gochiusa.com")
    illustOriginSite = params.get("originService", "不明")
    illustNsfw = params.get("nsfw", "0")
    illustNsfw = "1" if illustNsfw not in [0,"0","False","false"] else "0"
    #重複確認
    resp = g.db.get(
        "SELECT illustID FROM data_illust WHERE illustOriginUrl=%s AND illustOriginUrl <> 'https://gochiusa.com'",
        (illustOriginUrl,)
    )
    if resp:
        return jsonify(status=409, message="Specified image is already exist")
    #データ登録
    resp = g.db.edit(
        "INSERT INTO data_illust (artistID,illustName,illustDescription,illustDate,illustPage,illustLike,illustOriginUrl,illustOriginSite,userID,illustNsfw) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(artistID),
            g.validate(illustName,lengthMax=50, escape=False),
            g.validate(illustDescription,lengthMax=300),
            illustDate,
            illustPage,
            "0",
            illustOriginUrl,
            g.validate(illustOriginSite,lengthMax=20),
            str(g.userID),
            str(illustNsfw)
        ),
        False
    )
    if not resp:
        g.db.rollback()
        return jsonify(status=500, message="Server bombed.")
    # 登録した画像のIDを取得
    illustID = g.db.get("SELECT illustID FROM data_illust WHERE illustName=%s ORDER BY illustID DESC", (illustName,) )[0][0]
    #タグ情報取得/作成
    if "tag" in params.keys():
        for t in params["tag"]:
            if not g.db.has("info_tag","tagName=%s", (t,)):
                g.db.edit("INSERT INTO info_tag (userID,tagName,tagType,tagNsfw) VALUES (%s,%s,0,0)", (g.userID,t,), False)
            tagID = g.db.get("SELECT tagID FROM info_tag WHERE tagName=%s",(t,))[0][0]
            resp = g.db.edit("INSERT INTO data_tag (illustID,tagID) VALUES (%s,%s)",(str(illustID),str(tagID)), False)
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
    #キャラ情報取得/作成
    if "chara" in params.keys():
        for t in params["chara"]:
            if not g.db.has("info_tag","tagName=%s", (t,)):
                g.db.edit("INSERT INTO info_tag (tagName,tagType) VALUES (%s,1)", (t,), False)
            tagID = g.db.get("SELECT tagID FROM info_tag WHERE tagName=%s",(t,))[0][0]
            resp = g.db.edit("INSERT INTO data_tag (illustID,tagID) VALUES (%s,%s)",(str(illustID),str(tagID)), False)
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
    #画像の保存先フォルダ
    fileDirs = [
        os.path.join(current_app.config['ILLUST_FOLDER'], f)
        for f in ["orig","thumb","small","large"]
    ]
    isConflict = False
    try:
        with TemporaryDirectory() as tempFolder:
            fileOrigPath = os.path.join(tempFolder, f"{illustID}.raw")
            # 何枚目の画像を保存するかはURLパラメータで見る
            page = 0
            if "?" in params["imageUrl"]\
            and "192.168.0.3" not in params["imageUrl"]\
            and "cdn.gochiusa.team" not in params["imageUrl"]:
                query = parse_query(params["imageUrl"][params["imageUrl"].find("?")+1:])
                page = int(query["page"][0]) - 1
            # ツイッターから取る場合
            if params["imageUrl"].startswith("https://twitter.com/"):
                tg = TweetGetter()
                imgs = tg.getTweet(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                tg.downloadIllust(img_addr, fileOrigPath)
            # Pixivから取る場合
            elif params["imageUrl"].startswith("https://www.pixiv.net/"):
                ig = IllustGetter()
                imgs = ig.getIllust(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                ig.downloadIllust(img_addr, fileOrigPath)
            # ローカルから取る場合
            else:
                shutil.move(params["imageUrl"][params["imageUrl"].find("/static/temp/")+1:] ,fileOrigPath)
            # ハッシュ値比較
            hash = int(str(imagehash.phash(Image.open(fileOrigPath))), 16)
            is_match = g.db.get(
                "SELECT illustID, illustName, data_illust.artistID, artistName, BIT_COUNT(illustHash ^ %s) AS SAME FROM `data_illust` INNER JOIN info_artist ON info_artist.artistID = data_illust.artistID HAVING SAME = 0",
                (hash,)
            )
            if is_match:
                isConflict = True
                Exception('Conflict')
            origImg = createOrig(fileOrigPath)
            files = [
                origImg,
                createThumb(origImg),
                createSmall(origImg),
                createLarge(origImg)
            ]
        for data,dir in zip(files,fileDirs):
                data.save(
                    os.path.join(dir, f"{illustID}.png"),
                    compress_level=0
                )
                data.save(
                    os.path.join(dir, f"{illustID}.webp"),
                    lossless=True,
                    quality=90
                )
    except Exception as e:
        traceback.print_exc()
        for dir in fileDirs:
            for extension in ["PNG","WEBP"]:
                filePath = os.path.join(dir, f"{illustID}."+extension.lower())
                if os.path.exists(filePath):
                    os.remove(filePath)
        g.db.rollback()
        if isConflict:
            return jsonify(status=409, message="Specified image is already exist")
        else:
            return jsonify(status=400, message="bad request")
    g.db.commit()
    recordApiRequest(g.userID, "addArt", param1=illustID)
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
        "SELECT * FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID WHERE illustID = %s",
        (illustID,)
    )
    if not len(artData):
        return jsonify(status=404, message="The art data was not found.")
    artData = artData[0]
    #タグ情報取得
    tagData = g.db.get(
        "SELECT tagID,tagName,tagNsfw FROM data_tag natural join info_tag WHERE illustID = %s AND tagType=0",
        (illustID,)
    )
    #キャラ情報取得
    charaData = g.db.get(
        "SELECT tagID,tagName,tagNsfw FROM data_tag natural join info_tag WHERE illustID = %s AND tagType=1",
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
        "hash": artData[13],
        "artist": {
            "id": artData[2],
            "name": artData[14],
            "group": artData[15],
            "pixiv": artData[16],
            "twitter": artData[17],
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
        isExist = g.db.has("info_artist","artistID=%s",(params[p],))
        if not isExist:
            return jsonify(status=400, message="Specified artist was not found.")
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `data_illust` SET `%s`=%s WHERE illustID=%s"%(p),
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
    isExist = g.db.has("data_tag","illustID=%s AND tagID=%s",(illustID,tagID,))
    if not isExist:
        return jsonify(status=400, message="The tag is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `data_tag` "\
        + "WHERE illustID = %s AND tagID = %s",
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
        + "NATURAL JOIN (SELECT tagID FROM data_tag WHERE illustID=%s) WHERE tagType=0",
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
            "nsfw": r[3]
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
        tagID = int(params.get("tagID"))
        isExist = g.db.has("info_tag","tagID=%s",(tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has("data_tag","illustID=%s AND tagID=%s",(illustID,tagID,))
    if isExist:
        return jsonify(status=400, message="The tag is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "\
        + "VALUES (%s,%s);",
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
        tagID = int(params.get("charaID"))
    except:
        return jsonify(status=400, message="charaID is invalid, or not specified.")
    isExist = g.db.has("data_tag","illustID=%s AND tagID=%s",(illustID,tagID,))
    if not isExist:
        return jsonify(status=400, message="The character is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `data_tag` "\
        + "WHERE illustID = %s AND tagID = %s",
        (illustID,tagID)
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
        "SELECT * FROM info_tag "\
        + "NATURAL JOIN (SELECT tagID FROM data_tag WHERE illustID=%s) WHERE tagType=1",
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
            "nsfw": r[3]
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
        tagID = int(params.get("charaID"))
        isExist = g.db.has("info_tag","tagID=%s",(tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has("data_tag","illustID=%s AND tagID=%s",(illustID,tagID,))
    if isExist:
        return jsonify(status=400, message="The character is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "\
        + "VALUES (%s,%s);",
        (illustID,tagID)
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
        "UPDATE data_illust SET illustLike = illustLike + 1 WHERE illustID = %s",
        (illustID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    resp2 = g.db.get(
        "SELECT illustLike FROM data_illust WHERE illustID = %s",
        (illustID,)
    )
    return jsonify(status=200, message="Update succeed.", likes=resp2[0][0])
