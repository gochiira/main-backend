import requests


class BaseClient():
    def __init__(self, address, token):
        self.address = address
        self.headers = {
            "Authorization": "Bearer " + token,
            "ContentType": "application/json"
        }

    def post(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.post(
            self.address + endpoint,
            params=params,
            json=json,
            headers=self.headers,
            files=files
        )

    def get(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.get(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )

    def put(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.put(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )

    def delete(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.delete(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )
