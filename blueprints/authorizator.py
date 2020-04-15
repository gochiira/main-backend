from flask import g
from flask_httpauth import HTTPTokenAuth
from itsdangerous import JSONWebSignatureSerializer as Serializer

auth = HTTPTokenAuth('Bearer')
token_serializer = Serializer("USAGI_SERVICE")

'''
権限0: 一般ユーザ用
権限3: 投稿Bot専用
権限5: アカウント登録/非ログイン状態用
権限9: フルアクセス

Web管理者キーはこれ(いつかサイト上に難読化して埋め込むこと。) 権限:5
Bearer eyJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwic2VxIjoyLCJwZXJtaXNzaW9uIjo1fQ.5_UXRraCZuqOPs5X53czpm_pQhpEaudpSu5ujZOrbLU

全体管理者キー(絶対に載せないこと) 権限:9
Bearer eyJhbGciOiJIUzI1NiJ9.eyJpZCI6Miwic2VxIjoxLCJwZXJtaXNzaW9uIjo5fQ.tLS3QO91IWv80TyH_KZTHo6wMSG2csAN0jQFWk4Zo2U

投稿用管理者キー(スクレイピングした際にはこれで投稿) 権限:3
未登録
'''

'''
from functools import wraps
def permission_required(
    api_method,
    requiredPermission=0,
    acceptIfSameUserID=False,
    accountId = None
    ):
    @wraps(api_method)
    def check_permission(*args, **kwargs):
        if (g.userID == userID and acceptIfSameUserID)\
        or (g.permission > requiredPermission):
            return api_method(*args, **kwargs)
        else:
            return jsonify(status=400, message="You don't have enough permissions.")
    return check_permission
'''

@auth.verify_token
def verify_token(token):
    g.userID = None
    try:
        data = token_serializer.loads(token)
        print(data)
    except:  # noqa: E722
        print("VerifyFailed")
        return False
    if 'id' in data:
        g.userID = data['id']
        g.userApiSeq = data['seq']
        g.userApiKey = token
        g.userPermission = data['permission']
        if g.db.has(
            "data_user",
            "userID=%s AND userApiSeq=%s AND userPermission=%s",
            (g.userID, g.userApiSeq, g.userPermission)
        ):
            return True
    return False