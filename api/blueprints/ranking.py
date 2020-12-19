from flask import Blueprint, g, request, jsonify, current_app
from datetime import datetime, timedelta
from ..db_helper import (
    getMylistCountDict, getMylistedDict,
    getRankingCountResult, getRankingResult
)
from ..extensions import (
    auth, limiter, handleApiPermission, cache, record
)
import calendar


ranking_api = Blueprint('ranking_api', __name__)

#
# イラストのランキング関連
#


def getRanking(whereSql, sortMethod):
    illustCount = getRankingCountResult(whereSql)
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    return getRankingResult(whereSql, illustCount, sortMethod)


@ranking_api.route('/daily/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=500, query_string=True)
def getDailyViewsRanking():
    now = datetime.now()
    whereSql = f"""rankingYear={now.year}
        AND rankingMonth={now.month}
        AND rankingDay={now.day}"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/daily/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getDailyLikesRanking():
    now = datetime.now()
    whereSql = f"""rankingYear={now.year}
        AND rankingMonth={now.month}
        AND rankingDay={now.day}"""
    return getRanking(whereSql, "totalLike")


@ranking_api.route('/weekly/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getWeeklyViewsRanking():
    now = datetime.now()
    if now.month > 1:
        month_days = calendar.monthrange(now.year, now.month-1)[1]
    else:
        month_days = calendar.monthrange(now.year-1, 12)[1]
    whereSql = f"""rankingYear={now.year} AND (
        (rankingMonth={now.month} AND rankingDay>={now.day-7})
        OR
        (
            rankingMonth={now.month-1} AND
            rankingDay>={month_days-((now.day-7)*-1)}
        ))"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/weekly/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getWeeklyLikesRanking():
    now = datetime.now()
    if now.month > 1:
        month_days = calendar.monthrange(now.year, now.month-1)[1]
    else:
        month_days = calendar.monthrange(now.year-1, 12)[1]
    whereSql = f"""rankingYear={now.year} AND (
        (rankingMonth={now.month} AND rankingDay>={now.day-7})
        OR
        (
            rankingMonth={now.month-1} AND
            rankingDay>={month_days-((now.day-7)*-1)}
        ))"""
    return getRanking(whereSql, "totalLike")


@ranking_api.route('/monthly/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getMonthlyViewsRanking():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    whereSql = f"""rankingYear={year} AND rankingMonth={month}"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/monthly/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getMonthlyLikesRanking():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    whereSql = f"""rankingYear={year} AND rankingMonth={month}"""
    return getRanking(whereSql, "totalLike")
