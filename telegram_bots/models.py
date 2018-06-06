'''
Ниже информация для подключения через API (XML/HTTP), для отправки транзакционных SMS сообщений.
Логин: http_fishkaE_1
Пароль: VAJs1K
Имя отправителя (Sender ID): INFO-T  (Доступное имя отправителя для теста)
URL для подключения: http://smpp.ibatele.com/xml/
Ссылка для входа в личный кабинет (логин, пароль такой же как для API подключения): https://smpp.ibatele.com
'''


import datetime
import json

from django.db import models


def cut_city(address):
    try:
        return address.split('/')[0][:-1] + address.split('/')[2][1:]
    except:
        return address


def get_attr_text_by_info(info):
    if info.get('attr_names'):
        attr_text = ''.join(['[{}]'.format(x)
                             for x in info.get('attr_names', [])]) + '\n'
    else:
        attr_text = ''
    return attr_text


def get_address_text_by_info(info, cs=False, arrow=True):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if info.get('addresses'):
        address_text = ''
        if arrow and len(info.get('addresses', [])) > 1:
            f = info.get('addresses', [])[0]
            l = info.get('addresses', [])[-1]
            info['addresses'] = [f, l]
        for i in range(len(info.get('addresses', []))):
            address = info.get('addresses', [])[i].split(' *')[0]
            if cs:
                address = cut_city(address)
            letter = '(' + letters[i % len(letters)] + ') '
            address_text += letter + address + (' → ' if arrow else '\n')
    else:
        address_text = ''
    return (address_text[:-3] if arrow else address_text)


def get_price_text_by_info(info, showPrice, cashless):
    if not showPrice:
        return ''
    price = info.get('price', 0)
    if price > 0:
        return 'Стоимость ' + ('по безналу ' if cashless else '') + '{} руб.\n'.format(price)
    return ''


def get_full_order_descr(info, showPrice, cashless):
    return ('{}{}{}'.format(
        get_address_text_by_info(info, arrow=False),
        get_attr_text_by_info(info),
        get_price_text_by_info(info, showPrice, cashless)
    )).strip()


def get_order_descr(info):
    address_text = get_address_text_by_info(info, cs=True)
    if len(address_text) > 120:
        address_text = address_text[:117] + '...'
    return ('{}'.format(
        address_text
    )).strip()


class CityGroup(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return '{}'.format(self.name)


class City(models.Model):
    name = models.CharField(max_length=128)
    help_text = models.CharField(max_length=8192, blank=True, null=True)
    to_address_check = models.BooleanField()
    tarif = models.IntegerField(blank=True, null=True)
    group_id = models.IntegerField(blank=True, null=True)
    show_on_register = models.BooleanField()
    city_group = models.ForeignKey(CityGroup, blank=True, null=True)
    timezone = models.IntegerField()
    attrs = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.name)


class TaxifishkaClient(models.Model):
    city = models.ForeignKey(City, blank=True, null=True)
    phone = models.CharField(max_length=128, blank=True, null=True)
    uid = models.CharField(max_length=128, unique=True)
    state = models.CharField(max_length=128)
    info = models.CharField(max_length=16384, blank=True, null=True)
    untracked_orders = models.CharField(
        max_length=16384, blank=True, null=True)
    registered_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} {} {}'.format(self.city, self.phone, str(self.registered_date).split('.')[0])


class OrderHistory(models.Model):
    client = models.ForeignKey(TaxifishkaClient)
    info = models.CharField(max_length=16384, blank=True, null=True)
    finished = models.CharField(blank=True, null=True, max_length=256)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    order_id = models.CharField(blank=True, null=True, max_length=256)

    def __str__(self):
        return get_order_descr(json.loads(self.info))

    def full_descr(self, showPrice, cashless, client):
        corrected = self.created + datetime.timedelta(hours=5)
        order_time = (str(corrected.day) + '.' + str(corrected.month) + '.'
                      + str(corrected.year) + ' ' +
                      str(corrected.hour).zfill(2) + ':'
                      + str(corrected.minute).zfill(2) + '\n')
        if order_time == '19.10.2017 05:44\n':
            order_time = ''
        return '{}{}{}'.format(
            order_time if self.created else '',
            get_full_order_descr(json.loads(self.info), showPrice, cashless),
            ('' if self.finished is None else
             ('\nЗаказ выполнен' if self.finished == 'success' else '\nЗаказ прекращен'))
        )


class JuridicalClientGroup(models.Model):
    client_group_id = models.IntegerField()
    name = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return '{}-{}'.format(self.name, self.client_group_id)


class ClientFamily(models.Model):
    client = models.ForeignKey(TaxifishkaClient)
    phone = models.CharField(max_length=128)
    name = models.CharField(max_length=128)

    def __str__(self):
        return '{} for {}'.format(self.name, self.client.phone)


class Settings(models.Model):
    name = models.CharField(max_length=128)
    help_text = models.CharField(max_length=64000, blank=True, null=True)
    attrs = models.CharField(max_length=1024, blank=True, null=True)
    # polling_period = models.IntegerField()
    order_polling_period = models.IntegerField()

    def __str__(self):
        return '{}'.format(self.name)
