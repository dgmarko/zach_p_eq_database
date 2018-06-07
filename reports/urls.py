from django.conf.urls import re_path, url
from django.urls import path
from . import views
from .views import OutputData, TradeMatchView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', views.index, name='index'),
    path('datainput', views.input_data, name='input_data'),
    url(r'tradematch/$', login_required(TradeMatchView.as_view(success_url="tradematch")), name='trade_match'),
    path('output', login_required(OutputData.as_view(success_url="")), name='output'),

    path(r'^ajax/load-purchases/$', views.load_purchases, name='load_buys'),
]
