import json
import subprocess
import os
import string
import random
import re

import requests
import emoji
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

from ...taximaster.api import get_order_params_list, get_order_state, \
    get_info_by_order_id, send_sms, create_client_employee, get_client_info, \
    get_finished_orders
from ...yandexmaps.geocode import reverse_geocode
from ...models import City, OrderHistory, ClientFamily, Settings

from .tm_utils import *
from .taxifishka_const import *
from .taxifishka_utils import *
from .taxifishka_keyboards import *


def _resend_address(client, message):
    info = json.loads(client.info)
    if not info.get('last_address'):
        client.state = 'get_address'
        client.save()
        return ('Введите адрес ({})'.format(get_letter(len(info['addresses']) + 1)), get_error_address_keyboard(client))
    address = info.get('last_address', '')
    city = client.city.name
    answer = requests.post('http://taxifishka.com:33313/parse',
                           data={'city': city, 'address': address})
    if answer.json()['status'] == 0:
        address = answer.json()['data']['address']
        info['addresses'].append(address)
        info['cities'].append(city)
        try:
            address_info = get_info(address, client.city.name)
            TAXIFISHKA_BOT.sendLocation(
                client.uid, address_info['lat'], address_info['lon'])
        except Exception:
            pass
        client.info = json.dumps(info)
        client.state = 'confirm_address'
        client.save()
        return ('Адрес ({})\n{}'.format(get_letter(len(info['addresses'])), address),
                get_confirm_address_keyboard(client))
    else:
        client.info = json.dumps(info)
        client.state = 'get_address'
        client.save()
        return ('Адрес не распознан',
                get_error_address_keyboard(client))


def register_handler(message, client):
    if message.get('text') == '/register':
        client.state = 'get_phone'
        client.save()
        return ('Регистрация',
                get_request_contact_keyboard())
    else:
        client.state = 'force_new'
        client.save()
        return ('Ваша учетная запись не зарегистрирована. Начать регистрацию?',
                get_yesno_keyboard())


def force_register_handler(message, client):
    if message.get('text') == 'Да':
        return register_handler({'text': '/register'}, client)
    if message.get('text') == 'Нет':
        client.state = 'new'
        client.save()
        return 'Для заказа такси необходимо пройти регистрацию', []
    return ('Начать регистрацию?',
            get_yesno_keyboard())


def choose_city_handler(message, client):
    if message.get('text') in [x.name for x in City.objects.filter(show_on_register=True)]:
        try:
            client.city = City.objects.get(name=message.get('text'))
            if json.loads(client.info).get('restore_choose_city', '') == 'force_order':
                info = json.loads(client.info)
                del info['restore_choose_city']
                client.info = json.dumps(info)
                client.state = 'force_order'
                client.save()
                return ('Город изменен на {}'.format(message.get('text', '')),
                        get_force_order_keyboard())
            if json.loads(client.info).get('restore_choose_city', '') == 'get_address':
                info = json.loads(client.info)
                del info['restore_choose_city']
                client.info = json.dumps(info)
                client.state = 'get_address'
                client.save()
                TAXIFISHKA_BOT.sendMessage(client.uid,
                                           'Город изменен на {}'.format(message.get('text', '')))
                return _resend_address(client, message)
            if json.loads(client.info).get('restore_choose_city', '') == 'wait_order':
                info = json.loads(client.info)
                del info['restore_choose_city']
                client.info = json.dumps(info)
                client.state = 'wait_order'
                client.save()
                return ('Город изменен на {}'.format(message.get('text', '')),
                        get_start_keyboard(client))
            client.state = 'wait_order'
            client.save()
            return ('Введите адрес (A)',
                    get_start_keyboard(client))
        except Exception:
            return ('Неизвестный город. Выберите город из списка',
                    get_citys_keyboard())
    else:
        return ('Неизвестный город. Выберите город из списка',
                get_citys_keyboard())


def get_phone_handler(message, client):
    try:
        client.phone = normalize_phone(message['contact']['phone_number'])
        client.state = 'choose_city'
        client.save()
        return ('Выберите город', get_citys_keyboard())
    except KeyError:
        #phone = message.get('text')
        # if validate_phone(phone):
        #    client.phone = normalize_phone(phone)
        #    client.state = 'wait_order'
        #    client.save()
        #    return ('Введите адрес (A)',
        #            get_start_keyboard(client))
        return ('Регистрация',
                get_request_contact_keyboard())


def wait_menu_command_handler(message, client):
    if message.get('text', '') in ['Помощь']:
        help_text = client.city.help_text
        if not help_text:
            help_text = Settings.objects.get(name='default').help_text
        return (help_text, get_menu_keyboard())
    if message.get('text', '') in ['Архив заказов']:
        last = get_last_orders(client)
        if len(last) > 0:
            return(last,
                   get_menu_keyboard())
        else:
            return ('Заказов пока нет', get_menu_keyboard())
    if message.get('text', '') in ['Мои друзья']:
        client.state = 'get_family_member'
        client.save()
        return ('Выберите друга', get_family_keyboard(client))
    if message.get('text', '') in ['Профиль']:
        client.state = 'choose_profile_action'
        client.save()
        return (get_profile_info(client), get_profile_keyboard())
    if message.get('text', '') in ['Написать нам']:
        client.state = 'get_review'
        client.save()
        return ('Оставьте свой отзыв или предложение', get_back_keyboard())
    if message.get('text', '') in ['Назад']:
        client.state = 'wait_order'
        client.save()
        return ('Введите адрес (A)', get_start_keyboard(client))
    return ('Выберите действие',
            get_menu_keyboard())


def get_review_handler(message, client):
    if message.get('text', '') == 'Назад':
        client.state = 'wait_menu_command'
        client.save()
        return ('Выберите действие', get_menu_keyboard())
    if message.get('text'):
        review = 'Отзыв от клиента {} [{}]:\n{}'.format(
            client.phone, client.city.name, message.get('text', ''))
        TAXIFISHKA_BOT.sendMessage(REVIEW_CHANNEL, review)
    client.state = 'wait_menu_command'
    client.save()
    return ('Спасибо за отзыв!', get_menu_keyboard())


def choose_profile_action_handler(message, client):
    if message.get('text', '') in ['/logout', 'Выйти из профиля']:
        client.state = 'new'
        client.save()
        return ('Вы вышли из профиля', [])
    if message.get('text', '') in ['Назад']:
        client.state = 'wait_menu_command'
        client.save()
        return ('Выберите действие', get_menu_keyboard())
    return ('Выберите действие',
            get_profile_keyboard())


def get_family_member_handler(message, client):
    if message.get('text', '') in ['Добавить друга']:
        client.state = 'get_family_member_phone'
        client.save()
        return ('Введите номер друга', get_back_keyboard())
    if message.get('text', '') in ['Назад']:
        client.state = 'wait_menu_command'
        client.save()
        return ('Выберите действие', get_menu_keyboard())
    cf = ClientFamily.objects.filter(client=client)
    for c in cf:
        if (c.name + ' (' + c.phone + ')') == message.get('text', ''):
            info = json.loads(client.info)
            info['selected_family_member'] = c.phone
            client.info = json.dumps(info)
            client.state = 'get_family_member_action'
            client.save()
            return (c.name + '\n' + c.phone, get_family_member_keyboard())
    return ('Выберите действие',
            get_family_keyboard(client))


def get_family_member_action_handler(message, client):
    if message.get('text', '') in ['Назад']:
        client.state = 'get_family_member'
        client.save()
        return ('Выберите друга', get_family_keyboard(client))
    info = json.loads(client.info)
    try:
        fm = ClientFamily.objects.filter(phone=info.get(
            'selected_family_member', ''), client=client)[0]
    except:
        client.state = 'wait_menu_command'
        client.save()
        return ('...', get_menu_keyboard())
    if message.get('text', '') in ['Удалить']:
        client.state = 'confirm_delete_family_member'
        client.save()
        return ('Удалить друга?\n' + fm.name + '\n' + fm.phone,
                get_yesno_keyboard())
    if message.get('text', '') in ['Переименовать']:
        client.state = 'rename_family_member'
        client.save()
        return ('Введите новое имя друга\n' + fm.name + '\n' + fm.phone,
                get_back_keyboard())
    return ('Выберите действие',
            get_family_member_keyboard())


def confirm_delete_family_member_handler(message, client):
    info = json.loads(client.info)
    try:
        fm = ClientFamily.objects.filter(phone=info.get(
            'selected_family_member', ''), client=client)[0]
    except:
        client.state = 'wait_menu_command'
        client.save()
        return ('...', get_menu_keyboard())
    if message.get('text', '') in ['Да']:
        fm.delete()
        del info['selected_family_member']
        client.info = json.dumps(info)
        client.state = 'get_family_member'
        client.save()
        return ('Друг удален', get_family_keyboard(client))
    if message.get('text') in ['Нет']:
        client.state = 'get_family_member_action'
        client.save()
        return ('Выберите действие', get_family_member_keyboard())
    return ('Выберите действие',
            get_yesno_keyboard())


def rename_family_member_handler(message, client):
    info = json.loads(client.info)
    try:
        fm = ClientFamily.objects.filter(phone=info.get(
            'selected_family_member', ''), client=client)[0]
    except:
        client.state = 'wait_menu_command'
        client.save()
        return ('...', get_menu_keyboard())
    if message.get('text', '') in ['Назад']:
        client.state = 'get_family_member_action'
        client.save()
        return ('Выберите действие', get_family_member_keyboard())
    if not message.get('text', ''):
        return ('Необходимо ввести имя', get_back_keyboard())
    name = message.get('text', '')
    fm.name = name
    fm.save()
    info['selected_family_member'] = fm.phone
    client.info = json.dumps(info)
    client.state = 'get_family_member_action'
    client.save()
    return ('Друг переименован', get_family_member_keyboard())


def get_family_member_phone_handler(message, client):
    if message.get('text', '') in ['Назад']:
        client.state = 'get_family_member'
        client.save()
        return ('Выберите друга', get_family_keyboard(client))
    phone = message.get('text')
    if validate_phone(phone):
        phone = normalize_phone(phone)
        if phone == client.phone:
            client.state = 'get_family_member'
            client.save()
            return('Нельзя добавить свой телефон', get_family_keyboard(client))
        try:
            cf = ClientFamily.objects.get(phone=phone, client=client)
            client.state = 'get_family_member'
            client.save()
            return ('Этот номер уже добавлен', get_family_keyboard(client))
        except:
            pass
        code = ''.join(random.choice(string.digits) for _ in range(4))
        send_sms(HOST, PORT, API_KEY, phone, 'Код подтверждения ' + code)
        info = json.loads(client.info)
        info['code'] = code
        info['family_member_phone'] = phone
        client.info = json.dumps(info)
        client.state = 'confirm_family_member'
        client.save()
        return ('Введите код СМС', get_back_keyboard())
    return ('Номер телефона не распознан, попробуйте еще раз', get_back_keyboard())


def confirm_family_member_handler(message, client):
    if message.get('text', '') in ['Назад']:
        client.state = 'get_family_member_phone'
        client.save()
        return ('Введите телефон', get_back_keyboard())
    info = json.loads(client.info)
    if message.get('text', '') != info.get('code', '****'):
        client.state = 'get_family_member'
        client.save()
        return ('Неверный код подтверждения', get_family_keyboard(client))
    client.state = 'get_family_member_name'
    client.save()
    return ('Введите имя', get_back_keyboard())


def get_family_member_name_handler(message, client):
    if message.get('text', '') in ['Назад']:
        client.state = 'get_family_member_phone'
        client.save()
        return ('Введите телефон', get_back_keyboard())
    if not message.get('text', ''):
        return ('Необходимо ввести имя', get_back_keyboard())
    name = message.get('text', '')
    info = json.loads(client.info)
    phone = info.get('family_member_phone', '')
    client.info = '{}'
    client.state = 'get_family_member'
    client.save()
    cf = ClientFamily(client=client, phone=phone, name=name)
    cf.save()
    return ('Друг добавлен\n' + cf.name + '\n' + cf.phone, get_family_keyboard(client))


def get_history_handler(message, client):
    if message.get('text') in ['Назад']:
        client.state = 'wait_order'
        client.save()
        return ('Введите адрес (A)', get_start_keyboard(client))
    if load_order_by_descr(message.get('text', ''), client):
        client.state = 'confirm_order'
        client.save()
        return (get_order_text(client), get_before_order_keyboard())
    return 'Выберите маршрут', get_history_keyboard(client)


def order_handler(message, client):
    def logout_handler(message, client):
        client.state = 'new'
        client.save()
        return ('Вы вышли из профиля', [])

    def new_order_handler_force(message, client):
        client.state = 'force_order'
        client.save()
        return ('Введите адрес (A)',
                get_force_order_keyboard())

    def menu_handler(message, client):
        client.state = 'wait_menu_command'
        client.save()
        return ('Выберите действие', get_menu_keyboard())

    def bad_register_handler(message, client):
        return ('Ваша учетная запись уже зарегистрирована. Введите /logout для выхода',
                get_start_keyboard(client))

    def repeat_order_handler(message, client):
        if len(get_last_different_orders(client)) > 0:
            client.state = 'get_history'
            client.save()
            return('Выберите маршрут',
                   get_history_keyboard(client))
        else:
            return ('Заказов пока нет. Введите адрес (A)', get_start_keyboard(client))

    def change_city_handler(message, client):
        info = json.loads(client.info)
        info['restore_choose_city'] = 'wait_order'
        client.state = 'choose_city'
        client.info = json.dumps(info)
        client.save()
        return ('Выберите город', get_citys_keyboard())

    inner_handlers = {
        '/logout': logout_handler,
        'Заказать такси': new_order_handler_force,
        '/order': new_order_handler_force,
        '/register': bad_register_handler,
        'Меню': menu_handler,
        'История заказов': repeat_order_handler,
        'Сменить город': change_city_handler,
    }
    inner_handler = inner_handlers.get(
        message.get('text'), get_address_handler)
    return inner_handler(message, client)


def force_order_handler(message, client):
    if message.get('text') == 'Сменить город':
        info = json.loads(client.info)
        info['restore_choose_city'] = 'force_order'
        client.state = 'choose_city'
        client.info = json.dumps(info)
        client.save()
        return ('Выберите город', get_citys_keyboard())
    if message.get('text') == 'Назад':
        client.info = json.dumps({})
        client.state = 'wait_order'
        client.save()
        return ('Введите адрес (A)', get_start_keyboard(client))
    return get_address_handler(message, client)


def get_address_handler(message, client, prefix='', from_loc=False):
    if message.get('location'):
        client.state = 'get_address'
        client.save()
        if len(json.loads(client.info).get('addresses', [])) > 1:
            return (prefix + 'Введите адрес вручную',
                    get_error_address_keyboard(client))
        if len(json.loads(client.info).get('addresses', [])) == 1:
            info = json.loads(client.info)
            info['addresses'] = []
            info['cities'] = []
            client.info = json.dumps(info)
            client.save()
        address = reverse_geocode(
            message['location']['latitude'], message['location']['longitude'])
        if address is None:
            return (prefix + 'Не удалось определить адрес по координатам. Введите адрес вручную',
                    get_error_address_keyboard(client))
        if address['city'] != client.city.name.split(' ')[0]:
            cities = [x.name for x in City.objects.filter(
                show_on_register=True)]
            if address['city'] in cities:
                client.city = City.objects.get(name=address['city'])
                client.save()
                return get_address_handler({'text': '{}{}'.format(address['street'], address['home'])}, client,
                                           prefix='Город изменен на {}\n'.format(address['city']),
                                           from_loc=True)
            return ('Вы находитесь в другом городе. Введите адрес вручную',
                    get_error_address_keyboard(client))
        return get_address_handler({'text': '{}{}'.format(address['street'], address['home'])}, client, from_loc=True)
    if message.get('text') in ['/cancel', 'отмена', 'отказ', 'Отменить заказ']:
        client.state = 'wait_order'
        client.info = '{}'
        client.save()
        return ('Заказ прекращен\nВведите адрес (A)',
                get_start_keyboard(client))
    if message.get('text', '') == 'Сменить город':
        info = json.loads(client.info)
        info['restore_choose_city'] = 'get_address'
        client.state = 'choose_city'
        client.info = json.dumps(info)
        client.save()
        return ('Выберите город', get_citys_keyboard())
    if message.get('text', '') in ['0', '1', '2', '3', '4']:
        return '', []
    if message.get('text') == 'Назад':
        info = json.loads(client.info)
        if len(info.get('addresses', [])) == 0:
            client.info = '{}'
            client.state = 'wait_order'
            client.save()
            return('Введите адрес (A)', get_start_keyboard(client))
        if len(info.get('addresses', [])) >= 2 or (
                len(info.get('addresses', [])) == 1 and not client.city.to_address_check):
            client.state = 'confirm_order'
            client.save()
            return (get_order_text(client),
                    get_before_order_keyboard())
        client.state = 'confirm_address'
        client.save()
        return confirm_address_handler({'text': 'Да'}, client)
    if len(re.split('[\,\.]', message.get('text', ''))) > 1:
        return try_parse_many_cities(message, client)
    try:
        address = message.get('text')
        info = json.loads(client.info)
        info['last_address'] = address
        if info.get('addresses') is None:
            info['addresses'] = []
        if info.get('client_addresses') is None:
            info['client_addresses'] = []
        if info.get('cities') is None:
            info['cities'] = []
        city = get_city_or_default(address, client)
        address = address.lower().replace(city.lower(), '')
        answer = requests.post('http://taxifishka.com:33313/parse5',
                               data={'city': city, 'address': address})
        if answer.json()['status'] == 0:
            addresses = answer.json()['data']['address']
            addresses_keyboard = get_addresses_inline_keyboard(addresses)
            info['last_request'] = {
                'address': address,
                'city': city,
                'variants': addresses,
            }
            client.info = json.dumps(info)
            client.state = 'confirm_address'
            client.save()
            TAXIFISHKA_BOT.sendMessage(client.uid,
                                       prefix +
                                       'Адрес ({})\n{}'.format(get_letter(
                                           len(info['addresses']) + 1), address),
                                       reply_markup=get_confirm_address_keyboard(client))
            return ('Найдены варианты, выберите подходящий или уточните запрос',
                    addresses_keyboard)
        else:
            client.state = 'get_address'
            client.info = json.dumps(info)
            client.save()
            return (prefix + 'Адрес не распознан',
                    get_error_address_keyboard(client))
    except:
        client.state = 'wait_order'
        client.info = '{}'
        client.save()
        return (prefix + 'Сервис временно недоступен. Приносим извинения.',
                get_start_keyboard(client))


def try_parse_many_cities(message, client):
    comment = ''
    addresses = re.split('[\,\.]', message.get('text', ''))
    for address in addresses:
        if len(address.split('*')) > 1:
            comment = address.split('*')[1]
            break
    try:
        cities = []
        addresses_parsed = []
        for address in addresses:
            city = get_city_or_default(address, client)
            address_rep = address.lower().replace(city.lower(), '')
            answer = requests.post('http://taxifishka.com:33313/parse',
                                   data={'city': city, 'address': address_rep})
            if answer.json()['status'] == 0:
                address_parsed = answer.json()['data']['address']
                addresses_parsed.append(address_parsed)
                cities.append(city)
            else:
                return get_address_handler({'text': message.get('text', '').replace(',', ' ').replace('.', ' ')}, client)
        info = json.loads(client.info)
        info['addresses'] = info.get('addresses', []) + addresses_parsed
        info['cities'] = info.get('cities', []) + cities
        info['comment'] = comment
        price, coords = route_analysis(info.get(
            'cities', [client.city.name]), info.get('addresses'), info.get('attr_ids'))
        info['price'] = price
        client.info = json.dumps(info)
        client.state = 'confirm_order'
        client.save()
        return (get_order_text(client),
                get_before_order_keyboard())
    except:
        return get_address_handler({'text': message.get('text', '').replace(',', ' ').replace('.', ' ')}, client)


def confirm_address_handler(message, client):
    info = json.loads(client.info)
    if info.get('last_request'):
        if message.get('text', '') in ['0', '1', '2', '3', '4'] and len(
                info['last_request'].get('variants', [])) >= int(message.get('text')) + 1:
            info['addresses'].append(
                handle_point_address(info['last_request'].get('variants', [])[int(message.get('text'))]))
            info['cities'].append(info['last_request'].get('city'))
            info['client_addresses'].append(
                info['last_request'].get('address'))
            client.info = json.dumps(info)
            client.save()
            try:
                address_info = get_info(handle_point_address(
                    info['last_request'].get('variants', [])[int(message.get('text'))]),
                                        info['last_request'].get('city'))
                TAXIFISHKA_BOT.sendLocation(
                    client.uid, address_info['lat'], address_info['lon'])
            except Exception:
                pass
            TAXIFISHKA_BOT.sendMessage(client.uid,
                                       info['last_request'].get('variants', [])[int(message.get('text'))])
            return confirm_address_handler({'text': 'Да'}, client)
    if message.get('text') == 'Да':
        if len(info.get('addresses', [])) == 0:
            client.state = 'get_address'
            client.save()
            return ('Введите адрес (A)', get_error_address_keyboard(client))
        if len(info.get('addresses', [])) == 1:
            client.state = 'get_comment'
            client.save()
            comment = '\n*' + \
                info.get('comment') if info.get('comment') else ''
            return ('Введите подъезд или комментарий' + comment, get_comment_keyboard())
        else:
            price, coords = route_analysis(info.get(
                'cities', [client.city.name]), info.get('addresses'), info.get('attr_ids'))
            info['price'] = price
            client.state = 'confirm_order'
            client.info = json.dumps(info)
            client.save()
            return (get_order_text(client), get_before_order_keyboard())
    if message.get('text', '') == 'Назад':
        if len(info.get('addresses', [])) == 0:
            client.state = 'wait_order'
            client.info = '{}'
            client.save()
            return ('Введите адрес (A)',
                    get_start_keyboard(client))
        price, coords = route_analysis(info.get(
            'cities', [client.city.name]), info.get('addresses', []),
            info.get('attr_ids'))
        info['price'] = price
        client.info = json.dumps(info)
        client.state = 'get_address'
        client.save()
        return get_address_handler({'text': 'Назад'}, client)
        return ('Введите адрес ({})'.format(get_letter(len(info['addresses']) + 1)), get_error_address_keyboard(client))
    client.state = 'get_address'
    client.info = json.dumps(info)
    client.save()
    return get_address_handler(message, client)


def confirm_order_handler(message, client):
    if message.get('text') == 'Заказать':
        info = json.loads(client.info)
        city = client.city.name
        if json.loads(client.info).get('intercity'):
            cities = info.get('cities', [client.city.name])
            city = cities[len(cities) - 1]
        order_id = create_order(info.get('cities', [client.city.name]),  info.get(
            'addresses', []), client.phone, info.get('attr_ids'))
        if order_id == -1:
            client.state = 'wait_order'
            client.save()
            return ('Не удалось заказать такси...',
                    get_start_keyboard(client))
        create_observer(client, order_id)
        info['order_id'] = order_id
        client.info = json.dumps(info)
        client.state = 'process_order'
        client.save()
        order_history = OrderHistory(client=client, info=client.info, order_id=str(order_id),
                                     finished='no')
        order_history.save()
        set_75_attr(order_id)
        return ('Заказ создан',
                get_process_order_keyboard(client))
    if message.get('text', '') == 'Следующий адрес':
        info = json.loads(client.info)
        #if info.get('repeat_order'):
        #    del info['repeat_order']
        #    client.info = json.dumps(info)
        client.state = 'get_address'
        client.save()
        return ('Введите адрес ({})'.format(get_letter(len(info['addresses']) + 1)),
                get_error_address_keyboard(client))
    if message.get('text', '') == 'Подъезд или комментарий':
        client.state = 'get_comment'
        info = json.loads(client.info)
        info['override_comment'] = True
        client.info = json.dumps(info)
        client.save()
        comment = '\n*' + info.get('comment') if info.get('comment') else ''
        return ('Введите подъезд или комментарий' + comment, get_back_keyboard())
    if message.get('text', '') == 'Отменить заказ':
        client.state = 'wait_order'
        client.info = json.dumps({})
        client.save()
        return ('Заказ прекращен\nВведите адрес (A)',
                get_start_keyboard(client))
    if message.get('text', '') == 'Назад':
        info = json.loads(client.info)
        if info.get('repeat_order', False):
            client.info = '{}'
            client.state = 'get_history'
            client.save()
            return('Выберите маршрут',
                   get_history_keyboard(client))
        if len(info.get('addresses', [])) == 1:
            client.state = 'get_comment'
            client.save()
            comment = '\n* ' + \
                info.get('comment') if info.get('comment') else ''
            return ('Введите подъезд или комментарий' + comment, get_comment_keyboard())
        address = info['client_addresses'][-1]
        city = get_city_or_default(address, client)
        address = address.lower().replace(city.lower(), '')
        answer = requests.post('http://taxifishka.com:33313/parse5',
                               data={'city': city, 'address': address})
        if answer.json()['status'] == 0:
            addresses = answer.json()['data']['address']
            addresses_keyboard = get_addresses_inline_keyboard(addresses)
            info['last_request'] = {
                'address': address,
                'city': city,
                'variants': addresses,
            }
            prev_address = info['client_addresses'][-1].split(' *')[0]
            info['addresses'] = info['addresses'][:-1]
            info['cities'] = info['cities'][:-1]
            info['client_addresses'] = info['client_addresses'][:-1]
            client.info = json.dumps(info)
            client.state = 'confirm_address'
            client.save()
            TAXIFISHKA_BOT.sendMessage(client.uid, 'Адрес ({})\n{}'.format(get_letter(len(info['client_addresses']) + 1),
                                                                           prev_address),
                                       reply_markup=get_confirm_address_keyboard(client))
            return ('Найдены варианты, выберите подходящий или уточните запрос',
                    addresses_keyboard)
        else:
            client.state = 'get_address'
            client.info = json.dumps(info)
            client.save()
            return ('Адрес не распознан',
                    get_error_address_keyboard(client))
    if message.get('text') == 'Услуги':
        client.state = 'choose_attr'
        client.save()
        answer = get_order_params_list(HOST, PORT, API_KEY)
        if answer['code'] != 0:
            client.state = 'wait_order'
            client.info = json.dumps({})
            client.save()
            return ('Сервис временно недоступен. Приносим извинения',
                    get_start_keyboard(client))
        return ('Выберите услуги',
                get_attrs_keyboard(answer, client))
    address = json.loads(client.info).get('to', '')
    return ('Выберите действие',
            get_before_order_keyboard())


def choose_attr_handler(message, client):
    if message.get('text') == 'Назад':
        client.state = 'confirm_order'
        client.save()
        return ('Заказать такси?',
                get_before_order_keyboard())
    answer = get_order_params_list(HOST, PORT, API_KEY)
    if answer['code'] != 0:
        client.state = 'wait_order'
        client.info = json.dumps({})
        client.save()
        return ('Сервис временно недоступен. Приносим извинения',
                get_start_keyboard(client))
    for attr in answer['data']['order_params']:
        if message.get('text') == attr['name']:
            info = json.loads(client.info)
            if info.get('attr_ids') is None:
                info['attr_ids'] = []
            if info.get('attr_names') is None:
                info['attr_names'] = []
            if not attr['id'] in info['attr_ids']:
                info['attr_ids'].append(attr['id'])
                info['attr_names'].append(attr['name'])
            else:
                info['attr_ids'].remove(attr['id'])
                info['attr_names'].remove(attr['name'])
            price, coords = route_analysis(info.get(
                'cities', [client.city.name]), info.get('addresses', []), info.get('attr_ids'))
            info['price'] = price
            client.info = json.dumps(info)
            client.state = 'confirm_order'
            client.save()
            return (get_order_text(client), get_before_order_keyboard())
    return ('Выберите услуги',
            get_attrs_keyboard(answer, client))


def get_comment_handler(message, client):
    info = json.loads(client.info)
    if message.get('text') == 'Отменить заказ':
        client.info = '{}'
        client.state = 'wait_order'
        client.save()
        return ('Заказ прекращен\nВведите адрес (A)',
                get_start_keyboard(client))
    if message.get('text', '') == 'Назад':
        if info.get('override_comment', False):
            del info['override_comment']
            client.info = json.dumps(info)
            client.state = 'confirm_order'
            client.save()
            return (get_order_text(client), get_before_order_keyboard())
        #address = info['addresses'][-1]
        #city = info['cities'][-1]
        # try:
        #    address_info = get_info(address, city)
        #    TAXIFISHKA_BOT.sendLocation(
        #        client.uid, address_info['lat'], address_info['lon'])
        # except Exception:
        #    pass
        address = info['client_addresses'][-1]
        city = get_city_or_default(address, client)
        address = address.lower().replace(city.lower(), '')
        answer = requests.post('http://taxifishka.com:33313/parse5',
                               data={'city': city, 'address': address})
        if answer.json()['status'] == 0:
            addresses = answer.json()['data']['address']
            addresses_keyboard = get_addresses_inline_keyboard(addresses)
            info['last_request'] = {
                'address': address,
                'city': city,
                'variants': addresses,
            }
            prev_address = info['client_addresses'][-1].split(' *')[0]
            info['addresses'] = info['addresses'][:-1]
            info['cities'] = info['cities'][:-1]
            info['client_addresses'] = info['client_addresses'][:-1]
            client.info = json.dumps(info)
            client.state = 'confirm_address'
            client.save()
            TAXIFISHKA_BOT.sendMessage(client.uid, 'Адрес ({})\n{}'.format(get_letter(len(info['client_addresses']) + 1),
                                                                           prev_address),
                                       reply_markup=get_confirm_address_keyboard(client))
            return ('Найдены варианты, выберите подходящий или уточните запрос',
                    addresses_keyboard)
        else:
            client.state = 'get_address'
            client.info = json.dumps(info)
            client.save()
            return (prefix + 'Адрес не распознан',
                    get_error_address_keyboard(client))
    if message.get('text') != 'Пропустить':
        info['addresses'][0] = '{} *{}'.format(info['addresses'][0].split(' *')[
            0], message.get('text', ''))
        info['comment'] = message.get('text', '')
        client.info = json.dumps(info)
    else:
        info['addresses'][0] = '{}'.format(info['addresses'][0].split(' *')[0])
        if info.get('comment'):
            del info['comment']
        client.info = json.dumps(info)
    if len(info.get('addresses', [])) == 1 and client.city.to_address_check:
        client.state = 'get_address'
        client.save()
        return ('Введите адрес ({})'.format(get_letter(len(info['addresses']) + 1)), get_error_address_keyboard(client))
    price, coords = route_analysis(info.get(
        'cities', [client.city.name]), info.get('addresses', []),
        info.get('attr_ids'))
    info['price'] = price
    client.info = json.dumps(info)
    client.state = 'confirm_order'
    client.save()
    return (get_order_text(client), get_before_order_keyboard())


def process_order_handler(message, client):
    info = json.loads(client.info)
    order_id = info.get('order_id', -1)
    answer = get_order_state(HOST, PORT, API_KEY, order_id)
    if answer['code'] != 0:
        client.state = 'wait_order'
        client.save()
        return order_handler(message, client)
    state = answer['data'].get('state_kind', '')
    if state == '' or state == 'aborted' or state == 'finished':
        client.state = 'wait_order'
        client.save()
        return order_handler(message, client)
    if message.get('text') in ['/where', 'Узнать где автомобиль']:
        coords = answer['data'].get('crew_coords')
        if coords and coords.get('lat') and coords.get('lon') and answer['data'].get('confirmed', '') != 'not_confirmed':
            TAXIFISHKA_BOT.sendLocation(
                client.uid, coords.get('lat'), coords.get('lon'))
            return ('', get_process_order_keyboard(client))
        else:
            if answer['data'].get('confirmed', '') != 'not_confirmed' and answer['data'].get('state_kind', '') != 'new_order':
                car_description = answer['data'].get('car_color', '') + ' ' + answer['data'].get(
                    'car_mark', '') + ' ' + answer['data'].get('car_number', '')
                return ('Едет ' + car_description + '.\nНе удалось определить местоположение.',
                        get_process_order_keyboard(client))
            else:
                return ('Мы продолжаем поиск автомобиля',
                        get_process_order_keyboard(client))
    if message.get('text') in ['/cancel', 'отмена', 'отказ', 'Отменить заказ']:
        if state == 'client_inside':
            return ('Нельзя отменить заказ на данном этапе',
                    get_process_order_keyboard(client))
        if info.get('family_order', False):
            return ('Выберите ',
                    get_process_order_keyboard(client))
        info['cancel_restore_state'] = 'process_order'
        client.info = json.dumps(info)
        client.state = 'confirm_cancel'
        client.save()
        return ('Вы хотите отменить заказ?',
                get_yesno_keyboard())
    if message.get('text') in ['Завершить слежение']:
        if not info.get('family_order', False):
            return ('Ваш заказ уже создан! Выберите действие',
                    get_process_order_keyboard(client))
        else:
            uo = json.loads(client.untracked_orders)
            uo.append(order_id)
            client.untracked_orders = json.dumps(uo)
            client.info = '{}'
            client.state = 'wait_order'
            client.save()
            return ('Слежение прекращено. Введите адрес (A)', get_start_keyboard(client))
    if message.get('text') in ['Телефон водителя']:
        phone, name, assigned, incar = get_driver(order_id)
        if phone != 'FAIL':
            TAXIFISHKA_BOT.sendContact(client.uid, phone, name)
        return ('', get_process_order_keyboard(client))
    return ('Ваш заказ уже создан! Выберите действие',
            get_process_order_keyboard(client))


def confirm_cancel_handler(message, client):
    if message.get('text') == 'Да':
        info = json.loads(client.info)
        order_id = info.get('order_id')
        if order_id:
            abortOrderUtil(order_id)
        client.info = json.dumps({})
        client.state = 'wait_order'
        client.save()
        return ('Заказ прекращен\nВведите адрес (A)',
                get_start_keyboard(client))
    if message.get('text') == 'Нет':
        info = json.loads(client.info)
        client.state = info.get('cancel_restore_state', 'wait_order')
        try:
            del info['cancel_restore_state']
        except KeyError:
            pass
        client.info = json.dumps(info)
        client.save()
        keyboard = []
        if client.state == 'process_order':
            keyboard = get_process_order_keyboard(client)
        return ('Заказ не был прекращен', keyboard)
    return ('Вы хотите отменить заказ?',
            get_yesno_keyboard())


def end_order_handler(message, client):
    if client.state != 'process_order' and client.state != 'confirm_cancel':
        return ('', [])
    uo = json.loads(client.untracked_orders)
    if message.get('order_id', -1) in uo:
        return ('', [])
    price_text = ''
    info = json.loads(client.info)
    if info.get('cashless', None) is None:
        cashless = get_cashless(client)
    else:
        cashless = info.get('cashless')
    real_cashless = cashless
    answer = get_finished_orders(HOST, PORT, API_KEY, {'phone': client.phone})
    if answer.get('code', -1) == 0:
        for order in answer['data'].get('orders', []):
            if order.get('id', -2) == info.get('order_id', -1):
                real_cashless = order.get('bank_card_sum', -1) > 0 or order.get('cashless_sum', -1) > 0
    if (not check_client_juridical(client)) and (not info.get('price_showed') or
                                                 cashless != real_cashless):
        answer = get_info_by_order_id(HOST, PORT, '', {'order_id': info.get('order_id', -1),
        'fields': 'DISCOUNTEDSUMM'})
        if answer.get('code') == 0:
            price_text = str(answer['data'].get(
                'DISCOUNTEDSUMM')) + ' руб' + (' по безналу ' if real_cashless else '')
    else:
        message['answer'] = 'Спасибо за поездку!'
    client.info = json.dumps({})
    client.state = 'wait_order'
    client.save()
    try:
        oh = OrderHistory.objects.get(order_id=str(info.get('order_id', -1)))
        oh.finished = 'success'
        oh.save()
    except:
        pass
    #if message.get('answer', '').find('{PRICE}') != -1:
    #    set_75_attr(info.get('order_id', -1))
    return (message.get('answer', 'Спасибо.').replace('{PRICE}', price_text),
            get_start_keyboard(client))


def send_order_handler(message, client):
    if client.state != 'process_order' and client.state != 'confirm_cancel':
        return ('', [])
    uo = json.loads(client.untracked_orders)
    if message.get('order_id', -1) in uo:
        return ('', [])
    info = json.loads(client.info)
    try:
        if (not info.get('family_order', False)
                and message.get('answer', '...').find('Едет ') != -1):
            answer = get_order_state(
                HOST, PORT, API_KEY, message.get('order_id', -1))
            if answer['code'] == 0:
                coords = answer['data'].get('crew_coords')
                if (coords and coords.get('lat') and coords.get('lon')
                        and answer['data'].get('confirmed', '') != 'not_confirmed'):
                    TAXIFISHKA_BOT.sendLocation(
                        client.uid, coords.get('lat'), coords.get('lon'))
    except:
        pass
    mes = ''
    if info.get('family_order', False):
        mes += 'Друг {}({})\n'.format(info.get('real_name', ''), info.get('real_phone'))
    mes += message.get('answer', '...')
    if info.get('send_info', False):
        mes += '\n' + get_outer_order_info(client)
    return (mes, get_process_order_keyboard(client))


def price_order_handler(message, client):
    if client.state != 'process_order' and client.state != 'confirm_cancel':
        return ('', [])
    uo = json.loads(client.untracked_orders)
    if message.get('order_id', -1) in uo:
        return ('', [])
    if json.loads(client.info).get('price', -1) > 0:
        return ('', [])
    if check_client_juridical(client):
        return ('', [])
    answer = get_info_by_order_id(HOST, PORT, '', {'order_id': json.loads(
        client.info).get('order_id', -1), 'fields': 'DISCOUNTEDSUMM'})
    if answer.get('code') == 0:
        price = answer['data'].get('DISCOUNTEDSUMM')
        if price:
            cashless = get_cashless(client)
            info = json.loads(client.info)
            info['price_showed'] = True
            info['cashless'] = cashless
            client.info = json.dumps(info)
            client.save()
            price = 'Заказ выполнен. К оплате ' + \
                ('по безналу ' if cashless
                 else '') + str(price) + ' руб'
        else:
            price = 'Заказ выполнен. Ожидание оплаты.'
    return (price, get_process_order_keyboard(client))
