from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ticket_notifications/(?P<ticket_id>[^/]+)/$', consumers.TicketNotificationConsumer.as_asgi()),
]
