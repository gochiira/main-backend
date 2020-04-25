from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/arts"
params = {
    "title":"美味しい顔のチノちゃん！",
    "originService":"Twitter",
    "originUrl": "https://twitter.com/mozukun43/status/1252950803930742791",
    "imageUrl":"https://twitter.com/mozukun43/status/1252950803930742791",
    "artist":{
        "name":"もくず"
    },
    "tag": ["ランチ"],
    "chara":["香風智乃"]
}
# addArt
resp = cl.post(addEndpoint, json=params).json()
print(resp)


# getArt
#getEndpoint = "/arts/1"
#print(cl.get(getEndpoint).text)

'''
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