import telepot
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
import requests
import json as jsonlib
import time
import datetime
import urllib.parse
import hashlib
import sys


API_VERSION = '/common_api/1.0/'

HOST = 'https://fishka.dyndns.org'
PORT = 8089
API_KEY = '4aaoI4Pp8m98XBjT55BYL57lj09XF9fa1b5E0SaA'

BOT_TOKEN = '353439098:AAGdIo7Ngw3PkqNRyP0ryE6PJFPlC3hu6V4'
TAXIFISHKA_BOT = telepot.Bot(BOT_TOKEN)


def request(address, port, api_key, command, params, post=False, json=False):
    try:
        if json:
            paramsFunc = jsonParams
        else:
            paramsFunc = urlencodeParams
        headers = getHeaders(api_key, params, paramsFunc, json)
        URL = address + ':' + str(port) + API_VERSION + command
        if post:
            req = requests.post(URL, verify=False, headers=headers,
                                data=paramsFunc(params))
        else:
            req = requests.get(URL, params=params,
                               verify=False, headers=headers)
        return req.json()
    except:
        return {'code': -1, 'descr': 'application error', 'data': {}}


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


def get_order_state(address, port, api_key, order_id):
    params = {'order_id': order_id}
    return request(address, port, api_key, 'get_order_state', params, post=False, json=False)


def order_state_checker(uid, order_id, mode, period):
    def load_order_info(order_id):
        order_info = {
            'state': 'new_order',
            'confirmed': 'not_confirmed',
            'from': '',
            'to': '',
            'car': {
                'mark': '',
                'model': '',
                'color': '',
                'gos_number': ''
            }
        }
        answer = get_order_state(HOST, PORT, API_KEY, order_id)
        if answer['code'] != 0:
            order_info['state'] = 'aborted'
        else:
            order_info['from'] = answer['data'].get('source', '')
            order_info['to'] = answer['data'].get('destination', '')
            order_info['car']['mark'] = answer['data'].get('car_mark', '')
            order_info['car']['model'] = answer['data'].get('car_model', '')
            order_info['car']['color'] = answer['data'].get('car_color', '')
            order_info['car']['gos_number'] = answer['data'].get(
                'car_number', '')
            order_info['state'] = answer['data'].get('state_kind', '')
            order_info['state_id'] = answer['data'].get('state_id', -1)
            order_info['confirmed'] = answer['data'].get('confirmed', '')
        return order_info

    def get_car(car):
        scar = ''
        if car['color']:
            scar += car['color'] + ' '
        if car['mark']:
            scar += car['mark'] + ' '
        if car['model']:
            scar += car['model'] + ' '
        scar += car['gos_number']
        return scar

    order_info = load_order_info(order_id)
    order_info['state'] = 'new_order'
    while True:
        time.sleep(period)
        order_info_new = load_order_info(order_id)
        if order_info_new['state'] == 'aborted':
            requests.post('https://taxifishka.com/telegram/taxifishka-end-order', data={'chat_id': uid,
                                                                                        'order_id': order_id, 'text':
                                                                                        'Заказ прекращен'}, verify=False)
            break
        if order_info_new['state'] == 'finished':
            requests.post('https://taxifishka.com/telegram/taxifishka-end-order', data={'chat_id': uid,
                                                                                        'order_id': order_id,
                                                                                        'text': 'Заказ выполнен на сумму {PRICE}'},
                          verify=False)
            break
        if order_info_new['state'] == 'driver_assigned':
            if order_info_new.get('confirmed') == 'not_confirmed':
                order_info_new['state'] = 'new_order'
        if order_info_new['state'] != order_info['state']:
            if order_info_new['state'] == 'new_order' and order_info.get('confirmed', '') != 'not_confirmed':
                requests.post('https://taxifishka.com/telegram/taxifishka-send-order', data={'chat_id': uid,
                                                                                             'order_id': order_id,
                                                                                             'text': 'Заказ создан'},
                              verify=False)
            if order_info_new['state'] == 'driver_assigned' and get_car(order_info_new['car']):
                requests.post('https://taxifishka.com/telegram/taxifishka-send-order', data={'chat_id': uid,
                                                                                             'order_id': order_id,
                                                                                             'text': 'Едет {}'.format(get_car(order_info_new['car']))},
                              verify=False)
            if order_info_new['state'] == 'car_at_place' and get_car(order_info_new['car']):
                requests.post('https://taxifishka.com/telegram/taxifishka-send-order', data={'chat_id': uid,
                                                                                             'order_id': order_id,
                                                                                             'text': 'Ожидает {}'.format(get_car(order_info_new['car']))},
                              verify=False)
            if order_info_new['state'] == 'client_inside':
                requests.post('https://taxifishka.com/telegram/taxifishka-send-order', data={'chat_id': uid,
                                                                                             'order_id': order_id,
                                                                                             'text': 'С клиентом {}'.format(get_car(order_info_new['car']))},
                              verify=False)
        else:
            if get_car(order_info_new['car']) != get_car(order_info['car']) and order_info_new['state'] != 'new_order' and order_info.get('confirmed', '') != 'not_confirmed':
                requests.post('https://taxifishka.com/telegram/taxifishka-send-order', data={'chat_id': uid,
                                                                                             'order_id': order_id,
                                                                                             'text': 'Едет {}'.format(get_car(order_info_new['car']))},
                              verify=False)
        if order_info['state_id'] != 107 and order_info_new['state_id'] == 107:
            requests.post('https://taxifishka.com/telegram/taxifishka-price-order', data={'chat_id': uid, 'order_id': order_id, 'text': ''},
                          verify=False)
        order_info = order_info_new


uid = int(sys.argv[1])
order_id = int(sys.argv[2])
mode = sys.argv[3]
period = int(sys.argv[4])
order_state_checker(uid, order_id, mode, period)
