from flask import Blueprint, request, g, jsonify
from ..db_helper import (
    getSearchResult
)
from ..extensions import (
    auth, limiter, handleApiPermission, record
)

timeline_api = Blueprint('timeline_api', __name__)

#
# ユーザー別タイムライン
#


@timeline_api.route('/follow', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addFollow():
    if not request.is_json:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    params = request.get_json()
    if "followType" not in params.keys()\
            or "followID" not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    params = {p: g.validate(params[p]) for p in params.keys()}
    follow_type = params.get("followType")
    follow_id = params.get("followID")
    if g.db.has(
        "data_timeline",
        "followType=%s AND followID=%s",
        (follow_type, follow_id)
    ):
        return jsonify(status=400, message="You already following.")
    resp = g.db.edit(
        """INSERT INTO data_timeline
            (`userID`,`followType`, `followID`)
            VALUES (%s,%s,%s)""",
        (g.userID, follow_type, follow_id)
    )
    if resp:
        return jsonify(status=200, message="Follow succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@timeline_api.route('/unfollow', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def removeFollow(charaID):
    if not request.is_json:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    params = request.get_json()
    if "followType" not in params.keys()\
            or "followID" not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    params = {p: g.validate(params[p]) for p in params.keys()}
    follow_type = params.get("followType")
    follow_id = params.get("followID")
    if g.db.has(
        "data_timeline",
        "followType=%s AND followID=%s",
        (follow_type, follow_id)
    ):
        return jsonify(status=400, message="You already following.")
    resp = g.db.edit("DELETE FROM info_tag WHERE tagID = %s", (charaID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@timeline_api.route('/', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getTimeline():
    # あんまり長いと負荷がかかりそうなので制限が要るかも
    # タグID一覧フィルタを錬成
    tagIDs = g.db.get(
        """SELECT followID FROM `data_timeline` WHERE followType!=4
        AND userID=%s""",
        (g.userID,)
    )
    filterTag = '(' + ",".join([str(t[0]) for t in tagIDs]) + ')'
    filterTag = '(0)' if filterTag == "()" else filterTag
    # 絵師ID一覧フィルタを錬成
    artistIDs = g.db.get(
        """SELECT followID FROM `data_timeline` WHERE followType=4
        AND userID=%s""",
        (g.userID,)
    )
    filterArtist = '(' + ",".join([str(a[0]) for a in artistIDs]) + ')'
    filterArtist = '(0)' if filterArtist == "()" else filterArtist
    # 条件を満たすイラストIDを取得
    illustIDs = g.db.get(
        f"""SELECT
            DISTINCT illustID
        FROM (
            (
                SELECT illustID
                FROM data_tag
                WHERE tagID IN {filterTag}
            ) UNION (
                SELECT illustID
                FROM data_illust
                WHERE artistID IN {filterArtist}
            )
        ) AS T1"""
    )
    illustCount = len(illustIDs)
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    # さっきとったイラストIDを渡す
    filterIllustID = '(' + ",".join([str(i[0]) for i in illustIDs]) + ')'
    whereSql = f"illustID IN {filterIllustID}"
    resultTitle = "タイムライン"
    # 後は一般的な検索と共通
    return getSearchResult(whereSql, illustCount, resultTitle)
