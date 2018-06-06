import json
import emoji
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from ...models import City, OrderHistory, ClientFamily
from .taxifishka_utils import *


def get_citys_keyboard():
    CITYES = [x.name for x in City.objects.filter(show_on_register=True)]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in CITYES])


def get_yesno_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in ['Да', 'Нет']])


def get_request_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Отправить номер',
                                  request_contact=True)]])


def get_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=emoji.emojize(':question_mark: Помощь'))],
        [  # KeyboardButton(text='Профиль'),
            KeyboardButton(text=emoji.emojize(':envelope: Написать нам'))],
        [KeyboardButton(text=emoji.emojize(':family: Мои друзья')),
         KeyboardButton(text=emoji.emojize(':file_cabinet: Архив заказов'))],
        [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))],
    ])


def get_profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in
                  ['Выйти из профиля', emoji.emojize(':left_arrow: Назад')]])


def get_start_keyboard(client):
    variants = [
        # [KeyboardButton(text=emoji.emojize(':oncoming_taxi: Заказать такси'))]
    ]
    variants.append([KeyboardButton(text=emoji.emojize(':gear: Меню')),
                     KeyboardButton(text=emoji.emojize(':mag: Мое местоположение', use_aliases=True),
                                    request_location=True)])
    variants.append([KeyboardButton(text=emoji.emojize(':cityscape: Сменить город')),
                     KeyboardButton(text=emoji.emojize(':repeat: История заказов', use_aliases=True))])
    client.info = '{}'
    client.save()
    return ReplyKeyboardMarkup(
        keyboard=[x for x in variants])


def get_force_order_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=emoji.emojize(':mag: Мое местоположение', use_aliases=True),
                        request_location=True)],
        [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
    ])


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in [emoji.emojize(':prohibited: Отменить заказ')]])


def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in [emoji.emojize(':left_arrow: Назад')]])


def get_comment_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in ['Пропустить', emoji.emojize(':left_arrow: Назад')]])


def get_error_address_keyboard(client):
    info = json.loads(client.info)
    if len(info.get('addresses', [])) == 1 and not client.city.to_address_check:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
        ])
    if len(info.get('addresses', [])) == 1 and client.city.to_address_check:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
        ])
    if len(info.get('addresses', [])) < 1:
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=emoji.emojize(':mag: Мое местоположение', use_aliases=True),
                            request_location=True)],
            [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
        ])
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))],
    ])


def get_confirm_address_keyboard(client):
    if len(json.loads(client.info).get('addresses', [])) == 0:
        return ReplyKeyboardMarkup(keyboard=[
            #[#KeyboardButton(text='Нет'),
            # KeyboardButton(text='Да')],
            [KeyboardButton(text=emoji.emojize(':mag: Мое местоположение', use_aliases=True),
                            request_location=True)],
            [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
        ])
    return ReplyKeyboardMarkup(keyboard=[
        #[#KeyboardButton(text='Нет'),
        # KeyboardButton(text='Да')],
        [KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))]
    ])


def get_before_order_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=emoji.emojize(':oncoming_taxi: Заказать'))],
        [KeyboardButton(text='Следующий адрес')],
        [KeyboardButton(text='Подъезд или комментарий'),
         KeyboardButton(text='Услуги')],
        [KeyboardButton(text=emoji.emojize(':prohibited: Отменить заказ')),
         KeyboardButton(text=emoji.emojize(':left_arrow: Назад'))],
    ])


def get_attrs_keyboard(answer, client):
    attr_ids = [int(x) for x in client.city.attrs.split(';') if x != '']
    variants = []
    for attr in answer['data']['order_params']:
        if attr['id'] in attr_ids:
            if not attr['id'] in json.loads(client.info).get('attr_ids', []):
                variants.append(emoji.emojize(':heavy_check_mark:') + ' ' + attr['name'])
            if attr['id'] in json.loads(client.info).get('attr_ids', []):
                variants.append(emoji.emojize(':heavy_multiplication_x:') + ' ' + attr['name'])
    variants.sort()
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in variants]
        + [[emoji.emojize(':left_arrow: Назад')]])


def get_process_order_keyboard(client):
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


def get_history_keyboard(client):
    history = get_last_different_orders(client)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=str(x))] for x in list(history) + [emoji.emojize(':left_arrow: Назад')]])


def get_family_keyboard(client):
    family = [
        x.name + ' (' + x.phone + ')' for x in ClientFamily.objects.filter(client=client)]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in family + ['Добавить друга', emoji.emojize(':left_arrow: Назад')]])


def get_family_member_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=x)] for x in ['Переименовать', 'Удалить', emoji.emojize(':left_arrow: Назад')]])


def get_addresses_inline_keyboard(addresses):
    addresses = addresses[:3]
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=(cut_city(addresses[x])),
                                               callback_data=str(x))] for x in range(len(addresses))])
