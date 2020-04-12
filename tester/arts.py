from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/arts"
params = {
    "title":"ゆっくりチノちゃん",
    "originService":"描いた",
    "originUrl": "https://mobile.twitter.com/deep_omado",
    "imageUrl":"http://192.168.0.3:5000/static/temp/ZjE5NjU5ODc3M2NlNGQ5NWJmNTRjMWJkYWRhMTYwZmQ.raw",
    "artist":{
        "name":"お窓"
    },
    "tag": ["デジタル", "素人", "アイコン", "Twitterアイコン", "フリー素材", "黒歴史"],
    "chara":["香風智乃"],
}
# addArt
resp = cl.post(addEndpoint, json=params).json()
print(resp)
illustID = resp["illustID"]

'''
# getArt
getEndpoint = f"/arts/{illustID}"
print(cl.get(getEndpoint).text)

# editArt
putEndpoint = f"/arts/{illustID}"
params = {"illustDescription":"TestDescription"}
print(cl.put(putEndpoint, params=params).text)

# deleteArtTag
deleteEndpoint = f"/arts/{illustID}/tags"
params = {"tagID":"1"}
print(cl.delete(deleteEndpoint, json=params).text)

# getArtTag
getEndpoint = f"/arts/{illustID}/tags"
print(cl.get(getEndpoint).text)

# addArtTag
putEndpoint = f"/arts/{illustID}/tags"
params = {"tagID":"1"}
print(cl.put(putEndpoint, json=params).text)


# deleteArtCharacter
deleteEndpoint = f"/arts/{illustID}/characters"
params = {"charaID":"1"}
print(cl.delete(deleteEndpoint, json=params).text)

# getArtCharacter
getEndpoint = f"/arts/{illustID}/characters"
print(cl.get(getEndpoint).text)

# addArtCharacter
putEndpoint = f"/arts/{illustID}/characters"
params = {"charaID":"1"}
print(cl.put(putEndpoint, json=params).text)

# addArtLike
putEndpoint = f"/arts/{illustID}/likes"
print(cl.put(putEndpoint).text)

'''