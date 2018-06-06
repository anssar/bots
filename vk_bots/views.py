import json
import requests

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

ANDREY_TOKEN = 'e1a34841acae4eb98a1186609903c9df92ff1ab8b10098a0bdbd9abd27b6ce528ed95bc70c2368a84c7e6'

@csrf_exempt 
def andrey(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        if payload["type"] == "confirmation" and payload["group_id"] == 144048555:
            return HttpResponse('fd1b698d')
        if payload["type"] == "message_new":
            uid = payload["object"]["user_id"]
            requests.get('https://api.vk.com/method/messages.send?message={}&user_id={}&access_token={}&v=5.0'.format(
            "Иди нахуй", str(uid), ANDREY_TOKEN))
    except Exception:
        pass
    return HttpResponse('ok')
