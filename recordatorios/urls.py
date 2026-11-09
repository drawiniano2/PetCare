from django.urls import path
from . import views

urlpatterns = [
    path("", views.lista, name="recordatorios_lista"),
    path("vacunas/nueva/", views.vacuna_crear, name="recordatorios_vacuna_crear"),
    path("vacunas/<int:pk>/editar/", views.vacuna_editar, name="recordatorios_vacuna_editar"),
    path("controles/nuevo/", views.control_crear, name="recordatorios_control_crear"),
    path("controles/<int:pk>/editar/", views.control_editar, name="recordatorios_control_editar"),
]
