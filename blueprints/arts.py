from flask import Blueprint, g, request, jsonify, escape, current_app
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
from .worker import processConvertRequest
from .cache import apiCache
from datetime import datetime
from redis import Redis
from rq import Queue
import os
import tempfile
import json
import shutil
import traceback

arts_api = Blueprint('arts_api', __name__)

#
# イラストの投稿関連
#


# だいたい完成! (複数画像未サポート 画像重複確認未サポート
@arts_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createArt():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
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
    # 最低限のパラメータ確認
    params = request.get_json()
    if not params:
        return jsonify(status=400, message='bad request: not json')
    # パラメータ確認
    requiredParams = set(("title", "originService"))
    validParams = [
        "title",
        "caption",
        "imageUrl",
        "originUrl",
        "originService",
        "artist",
        "tag",
        "chara",
        "system",
        "group",
        "nsfw"
    ]
    # 必須パラメータ確認
    # print(params.items())
    params = {p: params[p] for p in params.keys() if p in validParams}
    if not requiredParams.issubset(params.keys()):
        return jsonify(status=400, message='bad request: not enough')
    # 作者パラメータ確認
    if "name" not in params["artist"]\
            and "twitterID" not in params["artist"]\
            and "pixivID" not in params["artist"]:
        return jsonify(status=400, message="Artist paramators are invalid.")
    # 画像パラメータ確認
    if not any([
        params["imageUrl"].startswith("https://twitter.com/"),
        params["imageUrl"].startswith("https://mobile.twitter.com/"),
        params["imageUrl"].startswith("https://www.pixiv.net/"),
        params["imageUrl"].startswith("https://api.gochiusa.team/static/temp/"),
        params["imageUrl"].startswith("http://192.168.0.3:5000/static/temp/")
    ]):
        return jsonify(status=400, message='bad request: not valid url')
    # バリデーションする
    params["title"] = g.validate(params.get(
        "title", "無題"), lengthMax=50, escape=False)
    params["caption"] = g.validate(
        params.get("caption", "コメントなし"), lengthMax=300)
    params["originService"] = g.validate(
        params.get("originService", "不明"), lengthMax=20)
    params["userID"] = g.userID
    # Workerにパラメータを投げる
    q = Queue(
        connection=Redis(host="192.168.0.10", port=6379, db=0),
        job_timeout=120,
        description=f'sUploadedImageConverter (Issued by User{g.userID})'
    )
    q.enqueue(processConvertRequest, params)
    recordApiRequest(g.userID, "addArt", param1=-1)
    return jsonify(status=202, message="Accepted")


@arts_api.route('/<int:illustID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def destroyArt(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    return jsonify(status=404, message="NotImplemented")


@arts_api.route('/<int:illustID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
@apiCache.cached(timeout=5)
def getArt(illustID):
    artData = g.db.get(
        """SELECT
            data_illust.illustID,
            illustName,
            illustDescription,
            illustDate,
            illustPage,
            illustLike,
            illustOriginUrl,
            illustOriginSite,
            illustNsfw,
            illustHash,
            illustExtension,
            data_illust.artistID,
            artistName,
            data_illust.userID,
            userName,
            illustStatus
        FROM
            data_illust
        INNER JOIN
            info_artist
        ON
            data_illust.artistID = info_artist.artistID
        INNER JOIN
            data_user
        ON
            data_illust.userID = data_user.userID
        WHERE
            illustID = %s""",
        (illustID,)
    )
    if not len(artData):
        return jsonify(status=404, message="The art data was not found.")
    artData = artData[0]
    # タグ情報取得
    tagDataList = g.db.get(
        "SELECT tagID,tagName,tagNsfw,tagType FROM data_tag natural join info_tag WHERE illustID = %s",
        (illustID,)
    )
    # リストを分ける
    tagData = [[t[0], t[1], t[2]] for t in tagDataList if t[3] == 0]
    charaData = [[t[0], t[1]] for t in tagDataList if t[3] == 1]
    groupData = [[t[0], t[1]] for t in tagDataList if t[3] == 2]
    systemData = [[t[0], t[1]] for t in tagDataList if t[3] == 3]
    # マイリストカウント取得
    mylistCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_mylist WHERE illustID = %s",
        (illustID,)
    )
    mylistCount = mylistCount[0][0] if mylistCount else 0
    # マイリスト済みか取得
    isMylisted = g.db.has(
        "data_mylist",
        "mylistID IN (SELECT mylistID FROM info_mylist WHERE userID=%s) AND illustID = %s",
        (g.userID, illustID)
    )
    return jsonify(status=200, data={
        "illustID": artData[0],
        "title": artData[1],
        "caption": artData[2],
        "date": artData[3].strftime('%Y-%m-%d %H:%M:%S'),
        "pages": artData[4],
        "like": artData[5],
        "mylist": mylistCount,
        "mylisted": isMylisted,
        "originUrl": artData[6],
        "originService": artData[7],
        "status": artData[15],
        "nsfw": artData[8],
        "hash": artData[9],
        "extension": artData[10],
        "artist": {
            "id": artData[11],
            "name": artData[12]
        },
        "user": {
            "id": artData[13],
            "name": artData[14]
        },
        "tag": tagData,
        "chara": charaData,
        "group": groupData,
        "system": systemData
    })


@arts_api.route('/<int:illustID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editArt(illustID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    # まず一旦タグを全部破壊
    resp = g.db.edit(
        "DELETE FROM data_tag WHERE illustID = %s",
        (illustID,)
    )
    # タグとキャラの追加
    for i, k in enumerate(["tag", "chara", "group", "system"]):
        if k in params.keys():
            for t in params[k]:
                # 存在しないタグは作成
                if not g.db.has("info_tag", "tagName=%s", (t,)):
                    g.db.edit(
                        "INSERT INTO info_tag (userID,tagName,tagType,tagNsfw) VALUES (%s,%s,%s,0)",
                        (g.userID, t, i),
                        False
                    )
                tagID = g.db.get(
                    "SELECT tagID FROM info_tag WHERE tagName=%s",
                    (t,)
                )[0][0]
                # タグIDのデータ挿入
                resp = g.db.edit(
                    f"INSERT INTO data_tag (illustID,tagID) VALUES ({illustID},{tagID})",
                    autoCommit=False
                )
                # 爆発したら 死亡を返す
                if not resp:
                    g.db.rollback()
                    return jsonify(status=500, message="Server bombed.")
    # 作者名の編集
    if "artist" in params.keys():
        # 同じ名前があるなら既存の作者のIDに変更する
        if g.db.has("info_artist", "artistName=%s", (params["artist"]["name"],)):
            artistID = g.db.get(
                "SELECT artistID FROM info_artist WHERE artistName=%s",
                (params["artist"]["name"],)
            )[0][0]
            resp = g.db.edit(
                "UPDATE data_illust SET artistID = %s WHERE illustID=%s",
                (artistID, illustID),
                autoCommit=False
            )
            # 古い方の作者IDはとりあえず放置しておく(GCで消し去る?)
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
        # そうでなければ今の作者の名前を変更する
        else:
            artistID = g.db.get(
                "SELECT artistID FROM data_illust WHERE illustID=%s",
                (illustID,)
            )[0][0]
            resp = g.db.edit(
                "UPDATE info_artist SET artistName = %s WHERE artistID=%s",
                (params["artist"]["name"], artistID)
            )
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
    validParams = {
        "artistId": "artistID",
        "title": "illustName",
        "caption": "illustDescription",
        "date": "illustDate",
        "page": "illustPage",
        "tag": "tag",
        "chara": "chara",
        "originUrl": "illustOriginUrl",
        "originService": "illustOriginSite",
        "illustLikeCount": "illustLike",
        "illustOwnerId": "userID",
        "nsfw": "illustNsfw",
        "status": "illustStatus"
    }
    params = {validParams[p]: params[p] for p in params.keys() if p in validParams.keys()}
    if not params:
        g.db.rollback()
        return jsonify(status=400, message="Request parameters are not satisfied.")
    for extra in ['tag', 'chara']:
        if extra in params.keys():
            del params[extra]
    if "artistID" in params.keys():
        isExist = g.db.has("info_artist", "artistID=%s", (params[p],))
        if not isExist:
            g.db.rollback()
            return jsonify(status=400, message="Specified artist was not found.")
    for p in params.keys():
        resp = g.db.edit(
            f"UPDATE data_illust SET {p}=%s WHERE illustID=%s",
            (params[p], illustID,),
            False
        )
        if not resp:
            g.db.rollback()
            return jsonify(status=500, message="Server bombed.")
    g.db.commit()
    return jsonify(status=200, message="Update succeed.")

#
# イラストのタグ関連
#   createArtTag は createArtと同時にされるので無い


@arts_api.route('/<int:illustID>/tags', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteArtTag(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        tagID = int(params.get("tagID"))
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if not isExist:
        return jsonify(status=400, message="The tag is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `data_tag` "
        + "WHERE illustID = %s AND tagID = %s",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")


@arts_api.route('/<int:illustID>/tags', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtTag(illustID):
    '''指定されたイラスト付属のタグ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        "SELECT * FROM info_tag "
        + "NATURAL JOIN (SELECT tagID FROM data_tag WHERE illustID=%s) WHERE tagType=0",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any tag.")
    return jsonify(
        status=200,
        message="found",
        data=[{
            "tagID": r[0],
            "name": r[1],
            "caption": r[2],
            "nsfw": r[3]
        } for r in resp]
    )


@arts_api.route('/<int:illustID>/tags', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtTag(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        tagID = int(params.get("tagID"))
        isExist = g.db.has("info_tag", "tagID=%s", (tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if isExist:
        return jsonify(status=400, message="The tag is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "
        + "VALUES (%s,%s);",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")

#
# イラストのキャラ関連
#   createArtCharacater は createArtと同時にされるので無い


@arts_api.route('/<int:illustID>/characters', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        tagID = int(params.get("charaID"))
    except:
        return jsonify(status=400, message="charaID is invalid, or not specified.")
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if not isExist:
        return jsonify(status=400, message="The character is not registered to the art.")
    resp = g.db.edit(
        "DELETE FROM `data_tag` "
        + "WHERE illustID = %s AND tagID = %s",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")


@arts_api.route('/<int:illustID>/characters', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    '''指定されたイラスト付属のキャラ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        "SELECT * FROM info_tag "
        + "NATURAL JOIN (SELECT tagID FROM data_tag WHERE illustID=%s) WHERE tagType=1",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any character.")
    return jsonify(
        status=200,
        message="found",
        data=[{
            "charaID": r[0],
            "name": r[1],
            "caption": r[2],
            "nsfw": r[3]
        } for r in resp]
    )


@arts_api.route('/<int:illustID>/characters', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        tagID = int(params.get("charaID"))
        isExist = g.db.has("info_tag", "tagID=%s", (tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(status=400, message="tagID is invalid, or not specified.")
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if isExist:
        return jsonify(status=400, message="The character is already registered to the art.")
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "
        + "VALUES (%s,%s);",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")

#
# イラストのいいね関連
#   無限にいいねできるものとする


@arts_api.route('/<int:illustID>/likes', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtLike(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
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
