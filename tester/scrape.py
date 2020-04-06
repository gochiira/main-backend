from base import BaseClient
import json
cl = BaseClient()

params = {"url":"https://twitter.com/miruzawa_akechi/status/1246438830011375617"}
scrapeEndpoint = "/scrape/twitter"
resp = cl.post(scrapeEndpoint, json=params).json()
print(resp)


# params = {"url":"https://www.pixiv.net/artworks/79707802"}
# scrapeEndpoint = "/scrape/pixiv"
# resp = cl.post(scrapeEndpoint, json=params).json()
# print(resp)