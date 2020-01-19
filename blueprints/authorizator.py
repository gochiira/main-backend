from flask import g
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

auth = HTTPTokenAuth('Bearer')
token_serializer = Serializer("USAGI_SERVICE")

'''
権限0: 一般ユーザ用
権限3: 投稿Bot専用
権限5: アカウント登録/非ログイン状態用
権限9: フルアクセス

Web管理者キーはこれ(いつかサイト上に難読化して埋め込むこと。) 権限:5
Bearer eyJhbGciOiJIUzI1NiIsImlhdCI6MTU3OTA4NDAzOCwiZXhwIjoxNTc5MDg3NjM4fQ.eyJpZCI6MSwic2VxIjoxLCJwZXJtaXNzaW9uIjo1fQ.Ba_dsvLlfZC3AMkuhLj8EEDBRpc0F4vJzMyGuLJc3vo

全体管理者キー(絶対に載せないこと) 権限:9
Bearer eyJhbGciOiJIUzI1NiIsImlhdCI6MTU3NTA1MzQxMywiZXhwIjoxNTc1MDU3MDEzfQ.eyJpZCI6Miwic2VxIjoxLCJwZXJtaXNzaW9uIjo5fQ.89pfKGGYisnaPQ8wiPF6IKJI5uaAxlpYl7YMSYVq1lo

投稿用管理者キー(スクレイピングした際にはこれで投稿) 権限:3
Bearer eyJhbGciOiJIUzI1NiIsImlhdCI6MTU3NTA1MzQzNSwiZXhwIjoxNTc1MDU3MDM1fQ.eyJpZCI6Mywic2VxIjoxLCJwZXJtaXNzaW9uIjozfQ.zxiRh9kJeiqJ9SRsGrh42xnAblODyrGS5bqKgoKyCDc
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
        g.userPermission = data['permission']
        if g.db.has(
            "user_main",
            "userID=? AND userApiSeq=? AND userPermission=?",
            (g.userID, g.userApiSeq, g.userPermission)
        ):
            return True
    return False