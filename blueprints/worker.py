from PIL import Image
from itsdangerous import JSONWebSignatureSerializer as Serializer
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs as parse_query
from .lib.seiga_client import SeigaGetter
from .lib.pixiv_client import IllustGetter
from .lib.twitter_client import TweetGetter
from .lib.notify_client import NotifyClient
from .db import SQLHandler
from imghdr import what as what_img
import os
import shutil
import imagehash
import traceback
import requests

'''
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


class UploadImageProcessor():
    def __init__(self, img_src):
        self.orig = self.createOrig(img_src)

    def shrinkImage(self, imgObj, targetX=640, targetY=480):
        '''指定サイズぐらいの画像を作る(既に指定したサイズ以下の場合はそのまま返す)'''
        x, y = imgObj.size
        if x <= targetX and y <= targetY:
            return imgObj
        if x > targetX:
            new_x = targetX
            hiritsu_x = new_x / x
            new_y = int(y * hiritsu_x)
            resp = imgObj.resize((new_x, new_y), Image.LANCZOS)
            return resp
        else:
            new_y = targetY
            hiritsu_y = new_y / y
            new_x = int(x * hiritsu_y)
            resp = imgObj.resize((new_x, new_y), Image.LANCZOS)
            return resp

    def getImageSize(self):
        h, w = self.orig.size
        return h, w

    def createOrig(self, img_src):
        # PNG/WEBPに変換する
        imgObj = Image.open(img_src).convert("RGB")
        return imgObj

    def createLarge(self):
        # 1280x960ぐらいに縮小する
        large = self.shrinkImage(self.orig, 1280, 960)
        return large

    def createSmall(self):
        # 640x480ぐらいに縮小する
        small = self.shrinkImage(self.orig, 640, 480)
        return small

    def createThumb(self, targetX=320, targetY=240):
        # サムネイルを作成する
        x, y = self.orig.size
        thumbnail = Image.new(
            "RGB",
            (targetX, targetY),
            (255, 255, 255)
        )
        new_y = targetY
        hiritsu_y = new_y / y
        new_x = int(x * hiritsu_y)
        cropped = self.orig.resize((new_x, new_y), Image.LANCZOS)
        thumbnail.paste(cropped, ((targetX-new_x)//2, 0))
        return thumbnail


class UploadLogger():
    def __init__(self, conn, userID):
        self.conn = conn
        self.uploadID = self.getUploadID(userID)

    def getUploadID(self, userID):
        resp = self.conn.edit(
            "INSERT INTO data_upload (uploadStatus,userID) VALUES (1, %s)",
            (userID,)
        )
        if not resp:
            self.conn.rollback()
            return ValueError('DB exploded')
        uploadID = self.conn.get(
            "SELECT MAX(uploadID) FROM data_upload WHERE userID=%s",
            (userID,)
        )
        if not uploadID:
            self.conn.rollback()
            return ValueError('DB exploded')
        return uploadID[0][0]

    def logStatus(self, status):
        resp = self.conn.edit(
            "UPDATE data_upload SET uploadStatus = %s WHERE uploadID = %s",
            (status, self.uploadID,),
            False
        )
        if not resp:
            self.conn.rollback()
            return ValueError('DB exploded')
        return True

    def logConvertedThumb(self):
        self.logStatus(2)
        self.conn.commit()
        return True

    def logConvertedSmall(self):
        self.logStatus(3)
        self.conn.commit()
        return True

    def logConvertedLarge(self):
        self.logStatus(4)
        self.conn.commit()
        return True

    def logCompleted(self, illustID):
        self.conn.edit(
            "UPDATE data_upload SET uploadStatus = 5, uploadFinishedDate = NOW(), illustID=%s WHERE uploadID = %s",
            (illustID, self.uploadID)
        )
        self.conn.commit()
        return True

    def logDuplicatedImageError(self):
        self.logStatus(8)
        self.conn.commit()
        return True

    def logServerExplodedError(self):
        self.logStatus(9)
        self.conn.commit()
        return True


def processConvertRequest(params):
    # バリデーションはエンドポイントでやっている前提
    # インスタンス作成
    conn = SQLHandler()
    userID = str(params["userID"])
    uploadLogger = UploadLogger(conn, userID)
    # パラメータを読み出す
    artistName = params["artist"].get("name", None)
    pixivID = params["artist"].get("pixivID", None)
    twitterID = params["artist"].get("twitterID", None)
    illustName = params.get("title", "無題")
    illustDescription = params.get("caption", "コメントなし")
    illustPage = 1
    illustOriginUrl = params.get("originUrl", "https://gochiusa.com")
    illustOriginSite = params.get("originService", "不明")
    illustNsfw = params.get("nsfw", "0")
    illustNsfw = "1" if illustNsfw not in [0, "0", "False", "false"] else "0"
    # 出典時点の重複確認(?page=1 まで含まれる)
    resp = conn.get(
        "SELECT illustID FROM data_illust WHERE illustOriginUrl=%s AND illustOriginUrl <> 'https://gochiusa.com'",
        (illustOriginUrl,)
    )
    if resp:
        uploadLogger.logDuplicatedImageError()
        return
    # 既存の作者でなければ新規作成
    if not conn.has(
        "info_artist",
        "artistName=%s OR pixivID=%s OR twitterID=%s",
        (artistName, pixivID, twitterID)
    ):
        resp = conn.edit(
            "INSERT INTO info_artist (artistName,twitterID,pixivID) VALUES (%s,%s,%s)",
            (artistName, pixivID, twitterID),
            False
        )
        if not resp:
            conn.rollback()
            uploadLogger.logServerExplodedError()
            conn.commit()
            return
    # 作者IDを取得する
    artistID = conn.get(
        "SELECT artistID FROM info_artist WHERE artistName=%s OR pixivID=%s or twitterID=%s",
        (artistName, pixivID, twitterID)
    )[0][0]
    # パラメータ時点のデータ登録
    resp = conn.edit(
        "INSERT INTO data_illust (artistID,illustName,illustDescription,illustPage,illustOriginUrl,illustOriginSite,userID,illustNsfw) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(artistID),
            illustName,
            illustDescription,
            illustPage,
            illustOriginUrl,
            illustOriginSite,
            userID,
            illustNsfw
        ),
        False
    )
    if not resp:
        conn.rollback()
        uploadLogger.logServerExplodedError()
        return
    # 登録した画像のIDを取得
    illustID = conn.get(
        "SELECT illustID FROM data_illust WHERE illustName=%s ORDER BY illustID DESC", (illustName,))[0][0]
    # 画像保存処理
    isConflict = False
    fileDir = "static/illusts/"
    try:
        with TemporaryDirectory() as tempFolder:
            fileOrigPath = os.path.join(tempFolder, f"{illustID}.raw")
            # 何枚目の画像を保存するかはURLパラメータで見る
            page = 0
            if "?" in params["imageUrl"]\
                    and "192.168.0.3" not in params["imageUrl"]\
                    and "cdn.gochiusa.team" not in params["imageUrl"]:
                query = parse_query(
                    params["imageUrl"][params["imageUrl"].find("?")+1:])
                page = int(query["page"][0]) - 1
                params["imageUrl"] = params["imageUrl"][:params["imageUrl"].find(
                    "?")]
            # ツイッターから取る場合
            if params["imageUrl"].startswith("https://twitter.com/"):
                tg = TweetGetter()
                imgs = tg.getTweet(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                tg.downloadIllust(img_addr, fileOrigPath)
            # ニコニコ静画から取る場合
            elif params["imageUrl"].startswith("https://seiga.nicovideo.jp/"):
                sg = SeigaGetter()
                img_addr = sg.getIllustSourceUrl(params["imageUrl"])
                sg.downloadIllust(img_addr, fileOrigPath)
            # Pixivから取る場合
            elif params["imageUrl"].startswith("https://www.pixiv.net/"):
                ig = IllustGetter()
                imgs = ig.getIllust(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                ig.downloadIllust(img_addr, fileOrigPath)
            # ローカルから取る場合
            else:
                shutil.move(params["imageUrl"][params["imageUrl"].find(
                    "/static/temp/")+1:], fileOrigPath)
            # 画像時点の重複確認(後日ファイルハッシュを使うようにする)
            hash = int(str(imagehash.phash(Image.open(fileOrigPath))), 16)
            '''
            is_match = conn.get(
                "SELECT illustID, illustName, data_illust.artistID, artistName, BIT_COUNT(illustHash ^ %s) AS SAME FROM `data_illust` INNER JOIN info_artist ON info_artist.artistID = data_illust.artistID HAVING SAME = 0",
                (hash,)
            )
            if is_match:
                isConflict = True
                raise Exception('Conflict')
            '''
            # Origデータを移動
            origType = what_img(fileOrigPath)
            if origType not in ["png", "jpg", "gif", "webp"]:
                with open(fileOrigPath, "rb") as f:
                    file = f.read()
                    if file[:2] != b'\xff\xd8':
                        raise Exception('Unknown file')
                    else:
                        origType = "jpg"
            # 正しい拡張子に変更
            shutil.move(fileOrigPath, fileOrigPath.replace("raw", origType))
            fileOrigPath = fileOrigPath.replace("raw", origType)
            fileSize = os.path.getsize(fileOrigPath)
            # 画像処理時点のデータ登録
            resp = conn.edit(
                "UPDATE data_illust "
                + "SET illustExtension=%s, illustHash=%s, illustBytes=%s "
                + "WHERE illustID = %s",
                (origType, hash, fileSize, illustID),
                False
            )
            if not resp:
                conn.rollback()
                uploadLogger.logServerExplodedError()
                return
            uploadConverter = UploadImageProcessor(fileOrigPath)
            # 画像の変換/保存処理
            # 元画像を保管
            shutil.move(
                fileOrigPath,
                os.path.join(
                    fileDir,
                    "orig",
                    f"{illustID}.{origType}"
                )
            )
            # それ以外は品質80で変換
            converts = {
                "thumb": [
                    uploadConverter.createThumb,
                    uploadLogger.logConvertedThumb
                ],
                "small": [
                    uploadConverter.createSmall,
                    uploadLogger.logConvertedSmall
                ],
                "large": [
                    uploadConverter.createLarge,
                    uploadLogger.logConvertedLarge
                ]
            }
            for c in converts.keys():
                dir = os.path.join(fileDir, c)
                img = converts[c][0]()
                for e in ["jpg", "webp"]:
                    img.save(
                        os.path.join(dir, f"{illustID}.{e}"),
                        quality=80
                    )
                converts[c][1]()
    except Exception as e:
        print(e)
        for folder in ["orig", "thumb", "small", "large"]:
            dir = os.path.join(fileDir, folder)
            for extension in ["png", "jpg", "webp", "gif"]:
                filePath = os.path.join(dir, f"{illustID}.{extension}")
                if os.path.exists(filePath):
                    os.remove(filePath)
        conn.rollback()
        if isConflict:
            uploadLogger.logDuplicatedImageError()
        else:
            uploadLogger.logServerExplodedError()
        return
    # 画像サイズ取得
    width, height = uploadConverter.getImageSize()
    resp = conn.edit(
        "UPDATE data_illust SET illustWidth = %s, illustHeight = %s WHERE illustID = %s",
        (width, height, illustID),
        False
    )
    if not resp:
        raise Exception("Image info set error")
    # システムタグ追加
    if not params["system"]:
        params["system"] = []
    if (width <= 720 and height <= 480)\
            or (height <= 720 and width <= 480):
        params["system"].append("SD")
    elif (width <= 1280 and height <= 720)\
            or (height <= 1280 and width <= 720):
        params["system"].append("HD")
    elif (width <= 1920 and height <= 1080)\
            or (height <= 1920 and width <= 1080):
        params["system"].append("FHD")
    elif (width <= 2560 and height <= 1440)\
            or (height <= 2560 and width <= 1440):
        params["system"].append("2K")
    else:
        params["system"].append("4K")
    # タグ情報取得作成
    # キャラ情報取得作成
    for i, k in enumerate(["tag", "chara", "group", "system"]):
        if k in params.keys():
            for t in params[k]:
                if not conn.has("info_tag", "tagName=%s", (t,)):
                    conn.edit(
                        "INSERT INTO info_tag (userID,tagName,tagType,tagNsfw) VALUES (%s,%s,%s,0)", (userID, t, i), False)
                tagID = conn.get(
                    "SELECT tagID FROM info_tag WHERE tagName=%s", (t,))[0][0]
                resp = conn.edit("INSERT INTO data_tag (illustID,tagID) VALUES (%s,%s)", (str(
                    illustID), str(tagID)), False)
                if not resp:
                    conn.rollback()
                    uploadLogger.logServerExplodedError()
                    return
    # 変換完了を記録
    uploadLogger.logCompleted(illustID)
    # 通知を送る
    notifier = NotifyClient(conn)
    notifier.sendArtNotify(illustID)
    # ユーザーにPYONを与える
    toymoneyKey = conn.get("SELECT userToyApiKey FROM data_user WHERE userID=%s", (userID,))[0][0]
    token_serializer = Serializer("UNSAFE_SECRET_KEY")
    toymoneyID = token_serializer.loads(toymoneyKey)['id']
    requests.post(
        "http://localhost:7070/users/transactions/create",
        json={"target_user_id": toymoneyID, "amount": 2},
        headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJpZCI6MCwic2VxIjoxLCJpc19hZG1pbiI6MH0.PNLYxn1Chr0iBSIqujI2ofWoq5gR-24EWQSwjG9h4M4"
        }
    )
    conn.close()
    return True


if __name__ == "__main__":
    params = {
        "title": "Test",
        "caption": "テストデータ",
        "originUrl": "元URL",
        "originService": "元サービス名",
        "imageUrl": "画像の元URL",
        "artist": {
            "name": "適当でも"
        },
        "tag": ["テスト"],
        "nsfw": 0
    }
    print("ok")
    conn = SQLHandler()
    uploadLogger = UploadLogger(conn, "3")
    print(uploadLogger.uploadID)
    # processConvertRequest(params)
