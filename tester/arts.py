from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/arts"
params = {
    "title":"女の子チノちゃん7",
    "originService":"Pixiv",
    "artist":{
        "name":"うみ猫"
    },
    "tag":["神絵師"],
    "chara":["香風智乃"],
}
files = {
    "file": open("test.jpg","rb"),
    "params": json.dumps(params)
}
# addArt
resp = cl.post(addEndpoint, files=files).json()
print(resp)
illustID = resp["illustID"]

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