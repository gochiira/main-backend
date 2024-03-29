from .upload_processor import UploadProcessor, UploadProcessorError
from ..db import SQLHandler
from ..scraper_lib.danbooru_client import DanbooruGetter
from ..scraper_lib.seiga_client import SeigaGetter
from ..scraper_lib.booth_client import BoothGetter
from ..scraper_lib.pixiv_client import IllustGetter
from ..scraper_lib.twitter_client import TweetGetter
from urllib.parse import parse_qs
import shutil
import os

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


def registerIllust(params):
    # インスタンス作成
    conn = SQLHandler(
        params["db"]["name"],
        params["db"]["host"],
        params["db"]["port"],
        params["db"]["user"],
        params["db"]["pass"]
    )
    processor = UploadProcessor(conn, params)
    try:
        # 出典アドレス
        origin_url = params["imageUrl"]
        # 出典重複検証
        processor.validateDuplication(origin_url)
        # 仮の情報登録をしてイラストIDを得る
        illust_id = processor.registerIllustInfo()
        # 画像保存先フォルダ
        static_dir = "static/illusts/"
        orig_path = os.path.join(
            static_dir,
            "orig",
            f"{illust_id}.raw"
        )
        real_orig_path = orig_path
        # 何枚目の画像を保存するかはURLパラメータで見る
        page = 0
        if "?" in origin_url and params["own_address"] not in origin_url:
            query = parse_qs(origin_url[origin_url.find("?")+1:])
            page = int(query["page"][0]) - 1
            origin_url = origin_url[:origin_url.find("?")]
        # ツイッターから取る場合
        if origin_url.startswith("https://twitter.com/"):
            tg = TweetGetter(
                params["twitter"][0],
                params["twitter"][1],
                params["twitter"][2],
                params["twitter"][3]
            )
            imgs = tg.getTweet(origin_url)['illust']['imgs']
            img_addr = imgs[page]["large_src"]
            tg.downloadIllust(img_addr, orig_path)
        # ニコニコ静画から取る場合
        elif origin_url.startswith("https://seiga.nicovideo.jp/"):
            sg = SeigaGetter(params["niconico"])
            img_addr = sg.getIllustSourceUrl(origin_url)
            sg.downloadIllust(img_addr, orig_path)
        # Danbooru
        elif origin_url.startswith("https://danbooru.donmai.us/"):
            dg = DanbooruGetter()
            img_addr = dg.getIllustSourceUrl(origin_url)
            dg.downloadIllust(img_addr, orig_path)
        # Boothから取る場合
        elif origin_url.startswith("https://booth.pm/ja/items/")\
                or "booth.pm/items/" in origin_url:
            bg = BoothGetter()
            imgs = bg.getIllustSourceUrl(origin_url)
            img_addr = imgs[page]
            bg.downloadIllust(img_addr, orig_path)
        # Pixivから取る場合
        elif origin_url.startswith("https://www.pixiv.net/"):
            ig = IllustGetter(params["pixiv"])
            imgs = ig.getIllust(origin_url)['illust']['imgs']
            img_addr = imgs[page]["large_src"]
            ig.downloadIllust(img_addr, orig_path)
        # ローカルから取る場合
        else:
            shutil.move(
                origin_url[origin_url.find("/static/temp/")+1:],
                orig_path
            )
        # 保存した画像を入力
        processor.setImageSource(orig_path)
        # 正しい拡張子を取得(不正なデータならここでエラーが返る)
        extension = processor.getIllustExtension()
        real_orig_path = orig_path.replace("raw", extension)
        shutil.move(
            orig_path,
            real_orig_path
        )
        # 解像度/ハッシュ/拡張子/ファイルサイズを登録
        filesize = os.path.getsize(real_orig_path)
        processor.registerIllustImageInfo(illust_id, filesize)
        # イラストタグを登録
        processor.registerIllustTags(illust_id)
        # 変換完了を記録
        processor.registerIllustInfoCompleted(illust_id)
        # 通知を送る
        processor.sendIllustInfoNotify(illust_id)
        # PYONを付与
        processor.givePyonToUser()
    except UploadProcessorError:
        if os.path.exists(orig_path):
            os.remove(orig_path)
        if os.path.exists(real_orig_path):
            os.remove(real_orig_path)
        return False
    else:
        return True
    finally:
        conn.close()


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
    from dotenv import load_dotenv
    load_dotenv(verbose=True, override=True)
    params["db"] = {
        "name": os.environ.get("DB_NAME"),
        "host": os.environ.get("DB_HOST"),
        "port": os.environ.get("DB_PORT"),
        "user": os.environ.get("DB_USER"),
        "pass": os.environ.get("DB_PASS")
    }
    params["toymoney"] = {
        "salt": os.environ.get("SALT_TOYMONEY"),
        "endpoint": os.environ.get("TOYMONEY_ENDPOINT"),
        "token": os.environ.get("TOYMONEY_TOKEN"),
        "amount": 2
    }
    registerIllust(params)
