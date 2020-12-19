from flask import g, request, jsonify


def getMylistCountDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistData = {
        i[0]: i[1]
        for i in g.db.get(
            "SELECT illustID, COUNT(mylistID) FROM data_mylist "
            + "GROUP BY illustID "
            + f"HAVING illustID IN ({illustKey})"
        )
    }
    mylistDict = {
        str(i): mylistData[i]
        if i in mylistData else 0
        for i in illustIDs
    }
    return mylistDict


def getMylistedDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistedData = g.db.get(
        f"""SELECT illustID FROM data_mylist
        WHERE mylistID IN
        (SELECT mylistID FROM info_mylist WHERE userID={g.userID})
        AND illustID IN ({illustKey})"""
    )
    mylistedData = [i[0] for i in mylistedData]
    mylistedDict = {
        str(i): True if i in mylistedData else False
        for i in illustIDs
    }
    return mylistedDict


def getSearchCountResult(whereSql, placeholder=()):
    illustCount = g.db.get(
        f"""SELECT COUNT(DISTINCT illustID) FROM data_illust
            WHERE {whereSql}""",
        placeholder
    )
    return illustCount[0][0]


def getRankingCountResult(whereSql, placeholder=()):
    illustCount = g.db.get(
        f"""SELECT COUNT(DISTINCT illustID) FROM data_i
        llust
            WHERE {whereSql}""",
        placeholder
    )
    return illustCount[0][0]


def getSearchResult(whereSql, illustCount, resultTitle, placeholder=()):
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        f"""SELECT illustID,data_illust.artistID,illustName,illustDescription,
        illustDate,illustPage,illustLike,
        illustOriginUrl,illustOriginSite,illustNsfw,artistName,
        illustExtension,illustStatus
        FROM data_illust INNER JOIN info_artist
        ON data_illust.artistID = info_artist.artistID
        WHERE {whereSql}
        AND illustStatus=0
        ORDER BY {sortMethod} {order}
        LIMIT {per_page} OFFSET {per_page * (pageID - 1)}""",
        placeholder
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    illustIDs = [i[0] for i in illusts]
    # マイリストされた回数を気合で取ってくる
    mylistDict = getMylistCountDict(illustIDs)
    # 自分がマイリストしたかどうかを気合で取ってくる
    mylistedDict = getMylistedDict(illustIDs)
    return jsonify(
        status=200,
        message="found",
        data={
            "title": resultTitle,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "mylist": mylistDict[str(i[0])],
                "mylisted": mylistedDict[str(i[0])],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
                "extension": i[11]
            } for i in illusts]
        }
    )


def getRankingResult(whereSql, illustCount, sortMethod):
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    pageID = pageID if pageID > 1 else 1
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        f"""SELECT
            data_illust.illustID,
            data_illust.artistID,
            illustName,
            illustDescription,
            illustDate,
            illustPage,
            SUM(data_ranking.illustLike) AS totalLike,
            SUM(data_ranking.illustView) AS totalView,
            illustOriginUrl,
            illustOriginSite,
            illustNsfw,
            artistName,
            illustExtension,
            illustStatus,
            rankingYear,
            rankingMonth,
            rankingDay
        FROM
            data_ranking
        INNER JOIN
            data_illust
        ON
            data_ranking.illustID = data_illust.illustID
        INNER JOIN
            info_artist
        ON
            data_illust.artistID = info_artist.artistID
        GROUP BY
            illustID
        HAVING
            {whereSql}
        ORDER BY
            {sortMethod} {order}
        LIMIT {per_page} OFFSET {per_page * (pageID - 1)}"""
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    illustIDs = [i[0] for i in illusts]
    # マイリストされた回数を気合で取ってくる
    mylistDict = getMylistCountDict(illustIDs)
    # 自分がマイリストしたかどうかを気合で取ってくる
    mylistedDict = getMylistedDict(illustIDs)
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "ランキング",
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": int(i[6]),
                "view": int(i[7]),
                "mylist": mylistDict[str(i[0])],
                "mylisted": mylistedDict[str(i[0])],
                "originUrl": i[8],
                "originService": i[9],
                "nsfw": i[10],
                "artist": {
                    "name": i[11]
                },
                "extension": i[12]
            } for i in illusts]
        })
