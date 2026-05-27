from django.urls import path
from . import views

urlpatterns = [
    path("zucchetti/", views.sync_view, name="zucchetti_sync"),
    path("zucchetti/generate-dat/", views.generate_dat_view, name="zucchetti_generate_dat"),
]
