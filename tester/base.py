import requests

'''
権限9
Bearer eyJhbGciOiJIUzI1NiJ9.eyJpZCI6Miwic2VxIjoxLCJwZXJtaXNzaW9uIjo5fQ.tLS3QO91IWv80TyH_KZTHo6wMSG2csAN0jQFWk4Zo2U

権限5
eyJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwic2VxIjoyLCJwZXJtaXNzaW9uIjo1fQ.5_UXRraCZuqOPs5X53czpm_pQhpEaudpSu5ujZOrbLU

'''

class BaseClient():
    def __init__(self,address="http://192.168.0.10:5000",token="eyJhbGciOiJIUzI1NiJ9.eyJpZCI6Miwic2VxIjoxLCJwZXJtaXNzaW9uIjo5fQ.tLS3QO91IWv80TyH_KZTHo6wMSG2csAN0jQFWk4Zo2U"):
        self.address = address
        self.headers = {
            "Authorization": "Bearer "+ token,
            "ContentType": "application/json"
        }
        
    def post(self, endpoint,params=None, data=None, json=None, files=None):
        return requests.post(
            self.address + endpoint,
            params=params,
            json=json,
            headers=self.headers,
            files=files
        )
        
    def get(self, endpoint,params=None,data=None,json=None, files=None):
        return requests.get(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )
        
    def put(self, endpoint,params=None,data=None,json=None, files=None):
        return requests.put(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )
        
    def delete(self, endpoint,params=None,data=None,json=None, files=None):
        return requests.delete(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )