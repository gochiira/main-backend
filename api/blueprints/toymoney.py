from flask import Blueprint, g, request, jsonify, escape
from ..extensions import (
    auth, limiter, handleApiPermission, record
)
import requests
from os import environ
from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)

toymoney_api = Blueprint('toymoney_api', __name__)
TOYMONEY_ENDPOINT = environ.get('TOYMONEY_ENDPOINT')


@toymoney_api.route(
    '/<path:text>',
    methods=["POST", "GET", "PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def torimochi(text):
    # 別サービスで使う認証トークンをDBから取ってくる
    toyApiKey = g.db.get(
        "SELECT userToyApiKey FROM data_user WHERE userID=%s",
        (g.userID,)
    )[0][0]
    headers = {"Authorization": f"Bearer {toyApiKey}"}
    path = request.path.replace("toymoney/", "")
    # GET/POST/PUT リクエストの内容をlocalhostで動く別サービスにリクエストする
    if request.method == "GET":
        resp = requests.get(
            TOYMONEY_ENDPOINT + path
            + '?' + request.query_string.decode("utf8"),
            headers=headers
        )
    else:
        data = request.get_json()
        if request.method == "POST":
            resp = requests.post(
                TOYMONEY_ENDPOINT + path,
                json=data,
                headers=headers
            )
        else:
            resp = requests.put(
                TOYMONEY_ENDPOINT + path,
                json=data,
                headers=headers
            )
    # 別サービスの応答を応答として返す
    return (resp.text, resp.status_code, resp.headers.items())
