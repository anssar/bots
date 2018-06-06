import json
import subprocess
import string
import random

import emoji
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

from ...taximaster.api import get_driver_info, get_current_orders_all,\
    get_order_state, get_current_orders, update_client_info,  get_client_info,\
    update_order, get_finished_orders, get_order_params_list, \
    get_info_by_order_id
from ...models import TaxifishkaClient, OrderHistory, JuridicalClientGroup,\
    ClientFamily, City, Settings

from .taxifishka_const import *
from .tm_utils import *


def get_process_order_keyboard_outer(client):
    info = json.loads(client.info)
    order_id = info.get('order_id', -1)
    variants = []
    phone, name, assigned, incar = get_driver(order_id)
    if assigned:
        variants = [emoji.emojize(':mag: Узнать где автомобиль', use_aliases=True)]
    if phone != 'FAIL':
        variants.append(emoji.emojize(':telephone_receiver: Телефон водителя'))
    if not info.get('family_order', False):
        if not incar:
            variants.append(emoji.emojize(':prohibited: Отменить заказ'))
    else:
        variants.append('Завершить слежение')
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in variants])


def set_75_attr(order_id):
    try:
        answer = get_order_state(HOST, PORT, API_KEY, order_id)
        if answer.get('code', -1) != 0:
            return
        attrs = answer.get('order_params', [])
        if not 75 in attrs:
            attrs.append(75)
        update_order(HOST, PORT, API_KEY, {
            'order_id': order_id,
            'order_params': attrs,
        })
    except:
        pass


def get_letter(n):
    s = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return s[(n - 1) % len(s)]


def cut_city(address):
    try:
        return address.split('/')[0][:-1] + address.split('/')[2] + (
            '/' + '/'.join(address.split('/')[3:]) if len(address.split('/')) > 3 else '')
    except:
        return address


def get_city_or_default(address, client):
    cityes = [x.name for x in City.objects.filter(
        city_group=client.city.city_group)]
    address = address.lower()
    for city in cityes:
        if address.find(city.split(' ')[0].lower()) != -1:
            return city
    return client.city.name


def get_profile_info(client):
    return 'Телефон: {}\nГород: {}'.format(client.phone, client.city.name)


def format_order_time(order_time):
    if not order_time:
        return ''
    year = order_time[:4]
    month = order_time[4:6]
    day = order_time[6:8]
    hour = order_time[8:10]
    minute = order_time[10:12]
    return '{}.{}.{} {}:{}\n'.format(day, month, year, hour, minute)


def format_order_addresses(source, destination, stops):
    n = 1
    ret = ''
    if not source:
        return ret
    ret += '({}) {}\n'.format(get_letter(n), source.split(' *')[0])
    n += 1
    for stop in stops:
        ret += '({}) {}\n'.format(get_letter(n),
                                 stop.get('address', 'Остановка').split(' *')[0])
        n += 1
    if not destination:
        return ret
    ret += '({}) {}\n'.format(get_letter(n), destination.split(' *')[0])
    return ret


def get_attrs(order_id, op):
    if order_id == -1:
        return ''
    answer = get_order_state(HOST, PORT, API_KEY, order_id)
    if answer.get('code', -1) != 0:
        return ''
    params = answer['data'].get('order_params', [])
    if len(params) < 1:
        return ''
    ret = ''
    for p in op:
        if p.get('id', -1) in params and p.get('id', -1) != 75 and p.get('id', -1) != 17:
            ret += '[{}]'.format(p.get('name', str(p.get('id', -1))))
    return (ret + '\n' if ret else '')

def get_result_price(order):
    price = order.get('total_sum', 0)
    if price == 0:
        return ''
    if price == order.get('cashless_sum', 0) and price != order.get('cash_sum', 0):
        return 'Стоимость по безналу {}руб\n'.format(price)
    ret = 'Стоимость {}руб\n'.format(price)
    if order.get('cashless_sum', 0) > 0:
        ret += 'Оплачено по безналу {}руб\n'.format(order.get('cashless_sum', 0))
    if order.get('bank_card_sum', 0) > 0:
        ret += 'Оплачено картой {}руб\n'.format(order.get('bank_card_sum', 0))
    if order.get('bonus_sum', 0) > 0:
        ret += 'Оплачено бонусами {}руб\n'.format(order.get('bonus_sum', 0))
    return ret

def format_price(order, showPrice):
    if not showPrice:
        return ''
    return get_result_price(order)


def format_status(order):
    state = order.get('state_id', -1)
    if state == -1:
        return ''
    if state == 21:
        return 'Заказ выполнен\n'
    else:
        return 'Заказ прекращен\n'


def get_full_order_descr(order, showPrice, params):
    order_time = format_order_time(order.get('start_time', ''))
    addresses = format_order_addresses(order.get('source', ''), order.get('destination', ''),
                                       order.get('stops', []))
    attrs = get_attrs(order.get('id', -1), params)
    price = format_price(order, showPrice)
    status = format_status(order)
    return '{}{}{}{}{}'.format(order_time, addresses, attrs, price, status)


def get_last_orders(client):
    answer = get_finished_orders(HOST, PORT, API_KEY, {'phone': client.phone})
    if answer.get('code', -1) != 0:
        return ''
    descrs = []
    orders = []
    showPrice = not check_client_juridical(client)
    params = []
    answerp = get_order_params_list(HOST, PORT, API_KEY)
    if answerp.get('code', -1) == 0:
        params = answerp['data'].get('order_params', [])
    for order in answer['data'].get('orders', []):
        orders.append(order)
    for order in orders[::-1]:
        descr = get_full_order_descr(order, showPrice, params)
        descrs.append(descr)
        if len(descrs) == 10:
            break
    return '\n'.join(descrs[::-1])


def get_order_descr_ldo(order):
    source = cut_city(order.get('source', '').split(' *')[0])
    destination = cut_city(order.get('destination', '').split(' *')[0])
    stops = order.get('stops', [])
    return '{}{}{}'.format(source, ('' if len(stops) == 0 else ' → ...'),
                           (' → ' + destination if destination else ''))


def get_last_different_orders(client):
    answer = get_finished_orders(HOST, PORT, API_KEY, {'phone': client.phone})
    if answer.get('code', -1) != 0:
        return ''
    descrs = []
    orders = []
    for order in answer['data'].get('orders', []):
        orders.append(order)
    for order in orders[::-1][:200]:
        if order.get('state_id', -1) == 21:
            descr = get_order_descr_ldo(order)
            if not descr in descrs:
                descrs.append(descr)
                if len(descrs) == 5:
                    break
    return descrs


def get_addresses(order):
    ret = []
    source = order.get('source', '').split(' *')[0]
    destination = order.get('destination', '').split(' *')[0]
    stops = order.get('stops', [])
    if source:
        ret.append(source)
    for stop in stops:
        if stop.get('address', ''):
            ret.append(stop.get('address').split(' *')[0])
    if destination:
        ret.append(destination)
    return ret

def handle_point_address(address):
    if address.find(' *') == -1 or len(address.split('/')) < 3:
        if address.find(' *') != -1:
            return address.split(' *')[0]
        return address
    else:
        city = address.split('/')[1]
        if address.split(' *')[1].find('.,') != -1:
            return address.split(' *')[1].replace('.,', '. /{}/, '.format(city))
        return address.split(' *')[0]


def get_city(address, client):
    try:
        return address.split('/')[1]
    except:
        return client.city.name


def get_cities(order, client):
    ret = []
    source = get_city(order.get('source', '').split(' *')[0], client)
    destination = get_city(order.get('destination', '').split(' *')[0], client)
    stops = order.get('stops', [])
    if source:
        ret.append(source)
    for stop in stops:
        if stop.get('address', ''):
            ret.append(get_city(stop.get('address').split(' *')[0], client))
    if destination:
        ret.append(destination)
    return ret


def get_comment(order):
    try:
        return order.get('source', '').split(' *')[1]
    except:
        return ''


def get_attrs_ldo(order):
    order_id = order.get('id', -1)
    op = []
    answer = get_order_params_list(HOST, PORT, API_KEY)
    if answer.get('code', -1) == 0:
        op = answer['data'].get('order_params', [])
    if order_id == -1:
        return [], []
    answer = get_order_state(HOST, PORT, API_KEY, order_id)
    if answer.get('code', -1) != 0:
        return [], []
    params = answer['data'].get('order_params', [])
    if len(params) < 1:
        return [], []
    ret_names = []
    for p in params:
        appended = False
        for p2 in op:
            if p2.get('id', -1) != 75 and p2.get('id', -1) != 17 and p2.get('id', -1) == p:
                ret_names.append(p2.get('name', 'параметр ' + str(p)))
                appended = True
        if not appended and p != 75 and p != 17:
            ret_names.append('параметр ' + str(p))
    return params, ret_names


def load_order_ldo(order, client):
    info = {}
    info['repeat_order'] = True
    info['addresses'] = get_addresses(order)
    info['client_addresses'] = get_addresses(order)
    info['cities'] = get_cities(order, client)
    info['comment'] = get_comment(order)
    attr_ids, attr_names = get_attrs_ldo(order)
    info['attr_ids'] = attr_ids
    info['attr_names'] = attr_names
    price, coords = route_analysis(info.get(
        'cities', [client.city.name]), info.get('addresses'), info.get('attr_ids'))
    info['price'] = price
    client.info = json.dumps(info)
    client.save()
    return True


def load_order_by_descr(descr, client):
    answer = get_finished_orders(HOST, PORT, API_KEY, {'phone': client.phone})
    if answer.get('code', -1) != 0:
        return False
    orders = []
    for order in answer['data'].get('orders', []):
        orders.append(order)
    for order in orders[::-1][:200]:
        if descr == get_order_descr_ldo(order):
            return load_order_ldo(order, client)
    return False


def get_client_id(client, force=False):
    phone = json.loads(client.info).get('real_phone', client.phone)
    answer = update_client_info(HOST, PORT, API_KEY, {
        'client_id': FAKE_CLIENT_ID,
        'phones': phone
    })
    if answer.get('code', -1) != 0 and answer.get('code', -1) != 101:
        return -1
    client_id = answer['data'].get('client_id', 0)
    answer = update_client_info(HOST, PORT, API_KEY, {
        'client_id': FAKE_CLIENT_ID,
        'phones': FAKE_CLIENT_PHONE
    })
    return client_id


def check_client_juridical(client):
    client_id = get_client_id(client)
    if client_id == -1 or client_id == '' or client_id == 0:
        return False
    answer = get_client_info(HOST, PORT, API_KEY, client_id)
    if answer.get('code') != 0:
        return False
    use_cashless = answer['data'].get('use_cashless', False)
    client_group_id = answer['data'].get('client_group_id', -1)
    try:
        JC = JuridicalClientGroup.objects.get(client_group_id=client_group_id)
        return use_cashless
    except:
        return False


def get_cashless(client):
    client_id = get_client_id(client)
    if client_id == -1 or client_id == '' or client_id == 0:
        return False
    answer = get_client_info(HOST, PORT, API_KEY, client_id)
    if answer.get('code') != 0:
        return False
    return answer['data'].get('use_cashless', False)


def get_comment_text_by_info(info):
    if info.get('comment', ''):
        comment_text = '*' + info.get('comment', '') + '\n'
    else:
        comment_text = ''
    return comment_text


def get_comment_text(client):
    info = json.loads(client.info)
    return get_comment_text_by_info(info)


def get_price_text(client):
    if check_client_juridical(client):
        return ''
    info = json.loads(client.info)
    price = info.get('price', 0)
    if price <= 0:
        price_text = ''
    else:
        price_text = ('Стоимость ' +
            ('по безналу ' if get_cashless(client) else '') +
            ('от ' if len(info.get('addresses', [])) == 1 else '') +
            '{} руб\n'.format(price))
    return price_text


def get_attr_text_by_info(info):
    if info.get('attr_names'):
        attr_text = ''.join(['[{}]'.format(x)
                             for x in info.get('attr_names', [])]) + '\n'
    else:
        attr_text = ''
    return attr_text


def get_attr_text(client):
    info = json.loads(client.info)
    return get_attr_text_by_info(info)


def get_address_text_by_info(info):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if info.get('addresses'):
        address_text = ''
        for i in range(len(info.get('addresses', []))):
            address = info.get('addresses', [])[i].split(' *')[0]
            letter = '(' + letters[i % len(letters)] + ') '
            address_text += letter + address + '\n'
    else:
        address_text = ''
    return address_text


def get_address_text(client):
    info = json.loads(client.info)
    return get_address_text_by_info(info)


def get_order_descr(info):
    return ('{}{}{}'.format(
        get_address_text_by_info(info),
        get_comment_text_by_info(info),
        get_attr_text_by_info(info)
    )).strip()


def get_order_text(client):
    return 'Заказать такси?\n{}{}{}{}'.format(
        get_address_text(client),
        get_comment_text(client),
        get_attr_text(client),
        get_price_text(client))


def create_observer(client, order_id, not_self=False):
    if not_self:
        mode = 'family'
    else:
        mode = 'normal'
    cmd = 'python3 /home/andrey/bots/telegram_bots/bots_settings/taxifishka/taxifishka_checker.py {} {} {} {}'.format(
        client.uid, order_id, mode, Settings.objects.get(name='default').order_polling_period)
    proc = subprocess.Popen(cmd, shell=True)


def get_driver(order_id):
    answer = get_order_state(HOST, PORT, API_KEY, order_id)
    if answer.get('code', -1) != 0:
        return 'FAIL', 'FAIL', False, False
    if answer['data'].get('confirmed', '') == 'not_confirmed' or answer['data'].get('confirmed', '') == '':
        return 'FAIL', 'FAIL', False, False
    incar = answer['data'].get('state_kind', '') == 'client_inside'
    assigned = answer['data'].get('confirmed', 'not_confirmed') != 'not_confirmed'
    driver_id = answer['data'].get('driver_id', -1)
    if driver_id == -1:
        return 'FAIL', 'FAIL', assigned, incar
    answer = get_driver_info(HOST, PORT, API_KEY, driver_id)
    if answer.get('code', -1) != 0:
        return 'FAIL', 'FAIL', assigned, incar
    name = answer['data'].get('name', '')
    phone = answer['data'].get('phones')[0].get('phone', 'FAIL')
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    return phone, name, assigned, incar


def delete_emoji(message, client):
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':gear:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':oncoming_taxi:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':left_arrow:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':prohibited:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':family:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':envelope:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':heavy_check_mark:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':heavy_multiplication_x:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':question_mark:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':file_cabinet:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':repeat:', use_aliases=True), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':mag:', use_aliases=True), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':cityscape:'), '').strip()
    message['text'] = message.get('text', '').replace(
        emoji.emojize(':telephone_receiver:'), '').strip()
    return message


def normalize_phone(phone):
    phone = phone.replace(' ', '').replace('+', '').replace('-', '')
    if len(phone) == 10:
        return '8' + phone
    else:
        return '8' + phone[1:]


def validate_phone(phone):
    phone = phone.replace(' ', '').replace('+', '').replace('-', '')
    if len(phone) != 10 and len(phone) != 11:
        return False
    if not phone.isdigit():
        return False
    if len(phone) == 10 and phone[0] != '9':
        return False
    if len(phone) == 11 and not (phone[:2] == '89' or phone[:2] == '79'):
        return False
    return True

def get_outer_order_info(client):
    return get_address_text(client) + get_comment_text(client) + get_price_text(client)


def load_order_for_client(order, client, self_order=True, cf_name=''):
    phone = order.get('phone')
    if client.state == 'process_order' or client.state == 'confirm_cancel':
        return
    if order.get('id', -1) in json.loads(client.untracked_orders):
        return
    info = {}
    info['addresses'] = [order.get('source', '')]
    if order.get('destination'):
        info['addresses'].append(order.get('destination', ''))
    info['attr_ids'] = order.get('order_params', [])
    try:
        info['cities'] = [
            order.get('source', '/' + client.city.name + '/').split('/')[1]]
    except IndexError:
        info['cities'] = [client.city.name]
    if order.get('destination'):
        try:
            info['cities'].append(
                order.get('destination').split('/')[1])
        except IndexError:
            info['cities'].append(client.city.name)
    info['order_id'] = order.get('id', -1)
    info['real_phone'] = order.get('phone', '')
    info['real_name'] = cf_name
    if not self_order:
        info['family_order'] = True
    price = 0
    try:
        answer = get_info_by_order_id(HOST, PORT, '', {'order_id': info.get('order_id', -1),
        'fields': 'DISCOUNTEDSUMM'})
        if answer.get('code') == 0:
            price = int(answer['data'].get('DISCOUNTEDSUMM', 0))
    except Exception:
        pass
    info['price'] = price
    try:
        info['comment'] = order.get('source', '').split(" *")[1]
    except IndexError:
        pass
    info['send_info'] = True
    client.info = json.dumps(info)
    client.state = 'process_order'
    client.save()
    create_observer(client, info['order_id'], not_self=(not self_order))
    if self_order:
        mes = 'Заказ создан\n' + get_outer_order_info(client)
    else:
        mes = 'Друг {} ({})\nЗаказ создан\n'.format(
            cf_name, info.get('real_phone', '')) + get_outer_order_info(client)
    TAXIFISHKA_BOT.sendMessage(client.uid, mes,
                               reply_markup=get_process_order_keyboard_outer(client))


def observe_orders():
    answer = get_current_orders_all(HOST, PORT, API_KEY)
    if answer.get('code', -1) != 0:
        return
    for order in answer['data'].get('orders', []):
        if order.get('creation_way', '') == 'taxophone':
            continue
        phone = order.get('phone')
        if phone:
            phone = normalize_phone(phone)
            try:
                try:
                    client = TaxifishkaClient.objects.get(phone=phone)
                    load_order_for_client(order, client)
                except:
                    pass
                cf = ClientFamily.objects.filter(phone=phone)
                for c in cf:
                    load_order_for_client(
                        order, c.client, self_order=False, cf_name=c.name)
            except ArithmeticError:
                continue
