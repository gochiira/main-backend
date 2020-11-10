import quart.flask_patch
from quart import Quart
from quart_cors import cors
from general import (
    app_before_request,
    app_after_request,
    app_teardown_appcontext,
    app_index, app_favicon,
    error_unauthorized,
    error_not_found,
    error_ratelimit,
    error_server_bombed
)
from blueprints import (
    accounts_api, artists_api, arts_api,
    catalog_api, characters_api, navigations_api,
    search_api, tags_api, scrape_api,
    news_api, notify_api, invites_api,
    superuser_api, mylist_api, toymoney_api,
    wiki_api, mute_api, uploaders_api,
    ranking_api,
    apiLimiter, apiCache
)
import json

'''
ごちイラAPI

<<アカウント>>
POST   /accounts
POST   /accounts/login/form
POST   /accounts/login/line
GET    /accounts/<int:accountId>
PUT    /accounts/<int:accountId>
DELETE /accounts/<int:accountId>
GET    /accounts/<int:accountId>/apiKey
GET    /accounts/<int:accountId>/favorites
PUT    /accounts/<int:accountId>/favorites
DELETE /accounts/<int:accountId>/favorites

<<作者>> 完成!
POST   /artists
DELETE /artists/<int:artistId>
GET    /artists/<int:artistId>
PUT    /artists/<int:artistId>

<<イラスト>> 完成! 16:38
POST   /arts
DELETE /arts/<int:artId>
GET    /arts/<int:artId>
PUT    /arts/<int:artId>
DELETE /arts/<int:artId>/tags
GET    /arts/<int:artId>/tags
PUT    /arts/<int:artId>/tags
DELETE /arts/<int:artId>/characters
GET    /arts/<int:artId>/characters
PUT    /arts/<int:artId>/characters
PUT    /arts/<int:artId>/stars

<<カタログ/リスト>> 完成!
GET /catalog/tags
GET /catalog/characters
GET /catalog/artists

<<キャラクター>> 完成!
POST   /characters
DELETE /characters/<int:tagId>
GET    /characters/<int:tagId>
PUT    /characters/<int:tagId>

<<ナビゲーションバー>> 完成!
GET /navigations/tags
GET /navigations/artists
GET /navigations/characters

<<検索>> 完成!
GET    /
GET    /tag
GET    /artist
GET    /character
GET    /keyword

<<タグ>> 完成!
POST   /tags
DELETE /tags/<int:tagId>
GET    /tags/<int:tagId>
PUT    /tags/<int:tagId>

<<スクレイピング>>
POST /scrape/twitter
POST /scrape/pixiv
POSt /scrape/upload

<<通報>>
POST /art/ID
POST /tag/ID
POST /user/ID

'''


def createApp():
    app = Quart(__name__)
    # 設定
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = 'USAGI_SERVICE'
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
    app.config['ILLUST_FOLDER'] = 'static/illusts'
    app.config['TEMP_FOLDER'] = 'static/temp'
    with open('blueprints/lib/imgur_auth.json', 'r') as f:
        app.config['imgurToken'] = json.loads(f.read())['token']
    with open('blueprints/lib/saucenao_auth.json', 'r') as f:
        app.config['saucenaoToken'] = json.loads(f.read())['token']
    with open('blueprints/lib/onesignal_auth.json', 'r') as f:
        data = json.loads(f.read())
        app.config['onesignalToken'] = data['token']
        app.config['onesignalAppId'] = data['appId']
    # 各ページルールを登録
    app.add_url_rule('/', 'index', app_index, strict_slashes=False)
    app.add_url_rule('/favicon.ico', 'favicon.ico', app_favicon)
    app.register_blueprint(accounts_api, url_prefix='/accounts')
    app.register_blueprint(artists_api, url_prefix='/artists')
    app.register_blueprint(arts_api, url_prefix='/arts')
    app.register_blueprint(catalog_api, url_prefix='/catalog')
    app.register_blueprint(characters_api, url_prefix='/characters')
    app.register_blueprint(navigations_api, url_prefix='/navigations')
    app.register_blueprint(search_api, url_prefix='/search')
    app.register_blueprint(tags_api, url_prefix='/tags')
    app.register_blueprint(scrape_api, url_prefix='/scrape')
    app.register_blueprint(news_api, url_prefix='/news')
    app.register_blueprint(notify_api, url_prefix='/notify')
    app.register_blueprint(invites_api, url_prefix='/invites')
    app.register_blueprint(superuser_api, url_prefix='/superuser')
    app.register_blueprint(mylist_api, url_prefix='/mylist')
    app.register_blueprint(toymoney_api, url_prefix='/toymoney')
    app.register_blueprint(wiki_api, url_prefix='/wiki')
    app.register_blueprint(mute_api, url_prefix='/mute')
    app.register_blueprint(uploaders_api, url_prefix='/uploaders')
    app.register_blueprint(ranking_api, url_prefix='/ranking')
    # リクエスト共通処理の登録
    app.before_request(app_before_request)
    app.after_request(app_after_request)
    app.teardown_appcontext(app_teardown_appcontext)
    # エラーハンドリングの登録
    app.register_error_handler(401, error_unauthorized)
    app.register_error_handler(404, error_not_found)
    app.register_error_handler(429, error_ratelimit)
    app.register_error_handler(500, error_server_bombed)
    # Flask-Limiterの登録
    apiLimiter.init_app(app)
    # Flask-Cacheの登録
    apiCache.init_app(app)
    # Flask-CORSの登録 (CORSは7日間キャッシュする)
    cors(
        app,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_origin=[
            "http://localhost:3000",
            "https://random.gochiusa.team",
            "https://illust.gochiusa.team"
        ],
        max_age=604800
    )
    return app


app = createApp()

if __name__ == '__main__':
    app.debug = True
    app.run(host="localhost")
