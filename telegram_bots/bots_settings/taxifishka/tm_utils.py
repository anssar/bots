import time
import datetime

from ...taximaster.api import create_order2, change_order_state,\
    get_addresses_like_house, get_addresses_like_points, analyze_route2,\
    calc_order_cost2, get_current_orders
from ...models import City

from .taxifishka_const import *


def tokenize_address(address):
    street = ''
    house = ''
    city = ''
    i = 0
    try:
        while not address[i].isalpha():
            i += 1
        while not address[i].isdigit():
            street += address[i]
            i += 1
        while address[i].isdigit():
            house += address[i]
            i += 1
        if (address[i] in ' /\\') or address[i].isalpha():
            house += address[i]
            i += 1
        while address[i].isdigit():
            house += address[i]
            i += 1
        city = address[i:]
    except IndexError:
        return normalize_street(street), house, city
    return normalize_street(street), house, city


def normalize_street(street):
    oldstreet = street
    street = ''
    for i in oldstreet:
        if i.isalpha() or i.isspace() or i.isdigit():
            street += i
        else:
            street += ' '
    while street.find('  ') != -1:
        street = street.replace('  ', ' ')
    return str.rstrip(street)


def get_info(address, selected_city):
    street, house, city = tokenize_address(address)
    if len(address.split(', ')) > 1:
        house = address.split(', ')[-1]
        street = ', '.join(address.split(', ')[:-1])
        answer = get_addresses_like_house(
            HOST, PORT, API_KEY, street, house, city=selected_city)
        if answer['code'] != 0:
            return None
    else:
        answer = get_addresses_like_points(
            HOST, PORT, API_KEY, address, city=selected_city)
        if answer['code'] != 0:
            return None
    ret = {}
    ret['address'] = address
    good_index = 0
    for i in range(len(answer['data']['addresses'])):
        if answer['data']['addresses'][i]['house'].replace(' ', '').lower() == house:
            good_index = i
    ret['lon'] = answer['data']['addresses'][good_index]['coords']['lon']
    ret['lat'] = answer['data']['addresses'][good_index]['coords']['lat']
    return ret

def get_minimal_cost(tarif, attr_ids):
    if not tarif:
        return 0
    params = {}
    params['tariff_id'] = tarif
    params['source_time'] = get_source_time()
    if attr_ids:
        params['order_params'] = attr_ids
    answer = calc_order_cost2(HOST, PORT, API_KEY, params)
    if answer['code'] != 0:
        return 0
    return answer['data']['sum']


def route_analysis(cities, addresses, attr_ids):
    city = get_city_util(cities[0])
    if len(addresses) == 1:
        return get_minimal_cost(city.tarif, attr_ids), []
    last_city = cities[-1]
    while len(cities) < len(addresses):
        cities.append(last_city)
    infos = []
    for i in range(len(addresses)):
        info = get_info(addresses[i].split(' *')[0], cities[i])
        infos.append(info)
    if len(infos) < 2:
        return 0, []
    answer = analyze_route2(HOST, PORT, API_KEY, infos)
    if answer['code'] != 0 and answer['code'] != 100:
        return 0, []
    route = (answer['data'].get('full_route_coords', [
        {'lat': x['lat'], 'lon': x['lon']} for x in infos
    ]) if all(infos) else [])
    params = {}
    if city.tarif:
        params['tariff_id'] = city.tarif
    if city.group_id:
        params['crew_group_id'] = city.group_id
    params['source_time'] = get_source_time()
    params['source_zone_id'] = answer['data']['addresses'][0]['zone_id']
    params['dest_zone_id'] = answer['data']['addresses'][-1]['zone_id']
    params['distance_city'] = answer['data']['city_dist']
    params['distance_country'] = answer['data']['country_dist']
    if answer['data']['country_dist'] > 0:
        params['is_country'] = True
    params['source_distance_country'] = answer['data']['source_country_dist']
    if attr_ids:
        params['order_params'] = attr_ids
    if len(answer['data']['addresses']) > 2:
        params['stops'] = []
        for i in range(1, len(answer['data']['addresses']) - 1):
            params['stops'].append(
                {'zone_id': answer['data']['addresses'][i]['zone_id']})
    answer = calc_order_cost2(HOST, PORT, API_KEY, params)
    if answer['code'] != 0:
        return 0, []
    return answer['data']['sum'], route


def get_city_util(city):
    try:
        city = City.objects.get(name=city)
    except:
        city = City.objects.get(name='Екатеринбург')
    return city


def get_coords(address, selected_city):
    if address == '':
        return [{'lat': 0, 'lon': 0}]
    street, house, city = tokenize_address(address)
    if len(address.split(', ')) > 1:
        house = address.split(', ')[-1]
        street = ', '.join(address.split(', ')[:-1])
        answer = get_addresses_like_house(
            HOST, PORT, API_KEY, street, house, city=selected_city)
        if answer['code'] != 0:
            return [{'lat': 0, 'lon': 0}]
    else:
        answer = get_addresses_like_points(
            HOST, PORT, API_KEY, address, city=selected_city)
        if answer['code'] != 0:
            return [{'lat': 0, 'lon': 0}]
    good_index = 0
    for i in range(len(answer['data']['addresses'])):
        if answer['data']['addresses'][i]['house'].replace(' ', '').lower() == house:
            good_index = i
    return [{'lon': answer['data']['addresses'][good_index]['coords']['lon'],
             'lat': answer['data']['addresses'][good_index]['coords']['lat']}]


def uniqOrder(from_address, to_address, phone):
    answer = get_current_orders(HOST, PORT, API_KEY, phone)
    if answer['code'] != 0:
        return False
    for order in answer['data']['orders']:
        if (order['source'].split(' *')[0] == from_address.split(' *')[0]):
            if order['destination'] == to_address:
                return False
    return True


def create_order(cities, addresses, phone, attr_ids):
    city = get_city_util(cities[0])
    if not uniqOrder(addresses[0], addresses[-1], phone):
        return -1
    last_city = cities[-1]
    while len(cities) < len(addresses):
        cities.append(last_city)
    infos = []
    for i in range(len(addresses)):
        info = get_info(addresses[i].split(' *')[0], cities[i])
        infos.append(info)
    if len(addresses) > 1:
        answer = analyze_route2(HOST, PORT, API_KEY, infos)
        if answer['code'] != 0:
            return -1
        params = {}
        if city.tarif:
            params['tariff_id'] = city.tarif
        params['addresses'] = answer['data']['addresses']
        for i in range(len(addresses)):
            params['addresses'][i]['address'] = addresses[i]
        params['phone'] = phone
        params['source_time'] = get_source_time()
        if city.group_id:
            params['crew_group_id'] = city.group_id
        if attr_ids:
            params['order_params'] = attr_ids
        answer = create_order2(HOST, PORT, API_KEY, params)
        if answer['code'] != 0:
            return -1
        return answer['data']['order_id']
    else:
        answer = analyze_route2(HOST, PORT, API_KEY, [infos[0], infos[0]])
        if answer['code'] != 0:
            return -1
        params = {}
        if city.tarif:
            params['tariff_id'] = city.tarif
        params['addresses'] = [answer['data']['addresses'][0]]
        params['addresses'][0]['address'] = addresses[0]
        params['phone'] = phone
        params['source_time'] = get_source_time()
        if city.group_id:
            params['crew_group_id'] = city.group_id
        if attr_ids:
            params['order_params'] = attr_ids
        answer = create_order2(HOST, PORT, API_KEY, params)
        if answer['code'] != 0:
            return -1
        return answer['data']['order_id']


def get_source_time():
    ret = ''
    now = datetime.datetime.now() + datetime.timedelta(hours=5, minutes=10)
    ret += str(now.year)
    ret += '0' * (2 - len(str(now.month))) + str(now.month)
    ret += '0' * (2 - len(str(now.day))) + str(now.day)
    ret += '0' * (2 - len(str(now.hour))) + str(now.hour)
    ret += '0' * (2 - len(str(now.minute))) + str(now.minute)
    ret += '0' * (2 - len(str(now.second))) + str(now.second)
    return ret


def abortOrderUtil(order_id):
    answer = change_order_state(HOST, PORT, API_KEY, order_id, 83)
