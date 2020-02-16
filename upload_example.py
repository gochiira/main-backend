import requests
import json

addr = "http://192.168.0.3:5000/arts"
filename = "hoge.jpg"

headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwic2VxIjoyLCJwZXJtaXNzaW9uIjo1fQ.5_UXRraCZuqOPs5X53czpm_pQhpEaudpSu5ujZOrbLU"
}

params = {
    "title":"女の子チノちゃん",
    "originService":"Pixiv",
    "artist":{
        "name":"うみ猫"
    },
    "tag":["神絵師"]
}
file = open(filename,"rb")

files = {
    "file": file,
    "params": json.dumps(params)
}

resp = requests.post(addr,headers=headers,files=files).text
print(resp)