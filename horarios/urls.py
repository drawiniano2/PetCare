from django.urls import path

from .views import (
    lista_horarios,
    crear_horario,
    editar_horario,
    cambiar_estado_horario,
)

app_name = "horarios"

urlpatterns = [
    path("", lista_horarios, name="lista"),
    path("nuevo/", crear_horario, name="nuevo"),
    path("<int:pk>/editar/", editar_horario, name="editar"),
    path(
        "<int:pk>/estado/",
        cambiar_estado_horario,
        name="cambiar_estado",
    ),
]
