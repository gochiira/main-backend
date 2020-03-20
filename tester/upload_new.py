import requests
import json

headers = {"Authorization":"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiaXNBZG1pbiI6dHJ1ZSwiaWF0IjoxNTgzNTc5Nzk1LCJleHAiOjE1ODYxNzE3OTV9.abqAtUInZczR4rD12vP1gvdLpvcgmB3fzhagT_0NQ0Y"}
files = {
    "files": (
        "test.jpg",
        open("test.jpg","rb"),
        "image/jpeg"
    )
}

response = requests.post(
    'http://localhost:1337/upload',
    files=files,
    headers=headers
)
print(response.text)