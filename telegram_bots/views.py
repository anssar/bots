import json
import sys
import traceback

import telepot.namedtuple

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from .bots_settings.taxifishka.taxifishka_const import *
from .bots_settings.taxifishka.taxifishka import TAXIFISHKA_COMMANDS
from .models import TaxifishkaClient, City

# def setwebhook(request):
#    print(TAXIFISHKA_BOT.setWebhook('https://taxifishka.com/telegram/taxifishka'))
#    return JsonResponse({}, status=200)


@login_required(login_url='/admin/')
@csrf_exempt
def notify(request):
    return render(request, 'notify.html', {'cityes': City.objects.all()})


@login_required(login_url='/admin/')
@csrf_exempt
def send_notify(request):
    message = request.POST.get('message', '')
    selected = json.loads(request.POST.get('selected', '{}'))
    clients = TaxifishkaClient.objects.all()
    for k in selected.keys():
        if selected[k] and message:
            for client in clients:
                if client.city.name == k:
                    TAXIFISHKA_BOT.sendMessage(client.uid, message)
    return JsonResponse({}, status=200)


@csrf_exempt
def taxifishka_check_orders(request):
    # TAXIFISHKA_BOT.sendMessage(58892069, 'check')
    message = {'text': TAXIFISHKA_CHECK_TOKEN}
    TAXIFISHKA_COMMANDS(message, None)
    return JsonResponse({}, status=200)


@csrf_exempt
def taxifishka_end_order(request):
    chat_id = request.POST.get('chat_id', 58892069)
    text = request.POST.get('text', '')
    order_id = request.POST.get('order_id', -1)
    message = {'text': TAXIFISHKA_END_TOKEN,
               'answer': text, 'order_id': order_id}
    try:
        client = TaxifishkaClient.objects.get(uid=chat_id)
    except Exception:
        return JsonResponse({}, status=200)
    answer, buttons = TAXIFISHKA_COMMANDS(message, client)
    if not answer:
        return JsonResponse({}, status=200)
    if not buttons:
        TAXIFISHKA_BOT.sendMessage(
            chat_id, answer, reply_markup=telepot.namedtuple.ReplyKeyboardRemove())
    else:
        TAXIFISHKA_BOT.sendMessage(chat_id, answer, reply_markup=buttons)
    return JsonResponse({}, status=200)


@csrf_exempt
def taxifishka_send_order(request):
    chat_id = request.POST.get('chat_id', 58892069)
    text = request.POST.get('text', '')
    order_id = request.POST.get('order_id', -1)
    message = {'text': TAXIFISHKA_SEND_TOKEN,
               'answer': text, 'order_id': order_id}
    try:
        client = TaxifishkaClient.objects.get(uid=chat_id)
    except Exception:
        return JsonResponse({}, status=200)
    answer, buttons = TAXIFISHKA_COMMANDS(message, client)
    if not answer:
        return JsonResponse({}, status=200)
    if not buttons:
        TAXIFISHKA_BOT.sendMessage(
            chat_id, answer, reply_markup=telepot.namedtuple.ReplyKeyboardRemove())
    else:
        TAXIFISHKA_BOT.sendMessage(chat_id, answer, reply_markup=buttons)
    return JsonResponse({}, status=200)


@csrf_exempt
def taxifishka_price_order(request):
    chat_id = request.POST.get('chat_id', 58892069)
    text = request.POST.get('text', '')
    order_id = request.POST.get('order_id', -1)
    message = {'text': TAXIFISHKA_PRICE_TOKEN,
               'answer': text, 'order_id': order_id}
    try:
        client = TaxifishkaClient.objects.get(uid=chat_id)
    except Exception:
        return JsonResponse({}, status=200)
    answer, buttons = TAXIFISHKA_COMMANDS(message, client)
    if not answer:
        return JsonResponse({}, status=200)
    if not buttons:
        TAXIFISHKA_BOT.sendMessage(
            chat_id, answer, reply_markup=telepot.namedtuple.ReplyKeyboardRemove())
    else:
        TAXIFISHKA_BOT.sendMessage(chat_id, answer, reply_markup=buttons)
    return JsonResponse({}, status=200)


@csrf_exempt
def taxifishka(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        callback_flag = False
        if payload.get('callback_query'):
            payload = payload['callback_query']
            callback_flag = True
        chat_id = payload['message']['chat']['id']
        if callback_flag:
            message = {'text': payload.get('data')}
        else:
            message = payload['message']
        try:
            client = TaxifishkaClient.objects.get(uid=chat_id)
        except Exception:
            client = TaxifishkaClient(
                uid=payload['message']['from']['id'], state='new', info=json.dumps({}), untracked_orders='[]')
            client.save()
        answer, buttons = TAXIFISHKA_COMMANDS(message, client)
        if answer:
            if not buttons:
                TAXIFISHKA_BOT.sendMessage(
                    chat_id, answer, reply_markup=telepot.namedtuple.ReplyKeyboardRemove())
            else:
                TAXIFISHKA_BOT.sendMessage(
                    chat_id, answer, reply_markup=buttons)
    except Exception as e:
        try:
            payload = json.loads(request.body.decode('utf-8'))
            if payload.get('edited_message') is None:
                TAXIFISHKA_BOT.sendMessage(
                    58892069, 'Ошибка ' + request.body.decode('utf-8')[:200] + '\n' + repr(e) + '\n' + traceback.format_exc())
        except Exception:
            TAXIFISHKA_BOT.sendMessage(
                58892069, 'Я не смог корректно обработать какое-то сообщение...')
    return JsonResponse({}, status=200)
