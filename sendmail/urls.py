from django.urls import path

from . import views

urlpatterns = [
    path("sendmail/", views.sendmail_index, name="sendmail_index"),
    path("sendmail/preview/", views.preview_email, name="sendmail_preview"),
]
