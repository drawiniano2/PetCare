from django.urls import path

from .views import lista_mascotas, detalle_mascota, crear_mascota, editar_mascota

app_name = "mascotas"

urlpatterns = [
    path("", lista_mascotas, name="lista"),
    path("nueva/", crear_mascota, name="crear"),
    path("<int:pk>/editar/", editar_mascota, name="editar"),
    path("<int:pk>/", detalle_mascota, name="detalle"),
]


