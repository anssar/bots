from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^taxifishka$', views.taxifishka),
    url(r'^taxifishka-end-order$', views.taxifishka_end_order),
    url(r'^taxifishka-send-order$', views.taxifishka_send_order),
    url(r'^taxifishka-price-order$', views.taxifishka_price_order),
    url(r'^taxifishka-check-orders$', views.taxifishka_check_orders),
    url(r'^notify$', views.notify),
    url(r'^send-notify$', views.send_notify),
    #url(r'^setwebhook$', views.setwebhook),
]
