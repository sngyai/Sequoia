# -*- encoding: UTF-8 -*-
import http.client
import json


def notify(msg=None):
    conn = http.client.HTTPSConnection("sngyai.com:5280")

    if msg is None or not msg:
        msg = "今日没有符合条件的股票"
    payload = json.dumps({"type": "headline",
                          "from": "admin@sngyai.com",
                          "to": "sequoia@sngyai.com",
                          "subject": "investing",
                          "body": msg})

    headers = {
        'authorization': "Basic YWRtaW5Ac25neWFpLmNvbTpTTjExMjM1OA==",
        'cache-control': "no-cache",
        }

    conn.request("POST", "/api/send_message", payload, headers)

    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))
