from django.conf.urls import url
from . import views as vk_views

urlpatterns = [
    url(r'^andrey$', vk_views.andrey),
#    url(r'^setwebhook$', views.setwebhook),
]
