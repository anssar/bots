import requests
import urllib.parse
import hashlib
import json as jsonlib
import xml.etree.ElementTree as ET
from copy import copy

API_VERSION = '/common_api/1.0/'
TAPI_VERSION = '/tm_tapi/1.0/'


def request(address, port, api_key, command, params, post=False, json=False, tapi=False):
    URL = address + ':' + str(port) + \
        (TAPI_VERSION if tapi else API_VERSION) + command
    if tapi:
        try:
            query = urlencodeParams(params)
            md5 = hashlib.md5()
            md5.update((query + api_key).encode())
            signature = md5.hexdigest()
            query += '&signature=' + signature
            if post:
                req = requests.post(URL, verify=False,
                                    data=query)
            else:
                req = requests.get(URL + '?' + query,
                                   verify=False)
            # return {'code': 0, 'data': req.text}
            return dictify(ET.fromstring(req.text))['response']
        except:
            return {'code': -1, 'descr': 'application error', 'data': {}}
    else:
        try:
            if json:
                paramsFunc = jsonParams
            else:
                paramsFunc = urlencodeParams
            headers = getHeaders(api_key, params, paramsFunc, json)
            if post:
                req = requests.post(URL, verify=False, headers=headers,
                                    data=paramsFunc(params))
            else:
                req = requests.get(URL, params=params,
                                   verify=False, headers=headers)
            return req.json()
        except:
            return {'code': -1, 'descr': 'application error', 'data': {}}


def dictify(r, root=True):
    if root:
        return {r.tag: dictify(r, False)}
    d = copy(r.attrib)
    if r.text and r.text not in ['\n']:
        try:
            return int(r.text)
        except ValueError:
            return r.text
    for x in r.findall("./*"):
        d[x.tag] = (dictify(x, False))
    if d == {}:
        return ''
    return d


def getHeaders(api_key, params, paramsFunc, json):
    headers = {}
    if json:
        headers['Content-Type'] = r'application/json'
    else:
        headers['Content-Type'] = r'application/x-www-form-urlencoded'
    headers['Signature'] = getSignature(api_key, params, paramsFunc)
    return headers


def getSignature(api_key, params, paramsFunc):
    md5 = hashlib.md5()
    md5.update((paramsFunc(params) + api_key).encode())
    return md5.hexdigest()


def urlencodeParams(params):
    return urllib.parse.urlencode(params)


def jsonParams(params):
    return jsonlib.dumps(params)
