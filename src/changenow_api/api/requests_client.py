import urllib.request
import urllib.parse
import json


def get(url, params=None):
    if params is None:
        params = {}
    query = urllib.parse.urlencode(params)
    request_url = '{}?{}'.format(url, query)
    req = urllib.request.Request(request_url)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req) as response:
        return json.load(response)


def post(url, body=None):
    if body is None:
        body = {}
    json_data = json.dumps(body)
    json_data_bytes = json_data.encode('utf-8')
    req = urllib.request.Request(url, json_data_bytes, method='POST')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req) as response:
        return json.load(response)
