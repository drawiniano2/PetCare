from .views import consultar_disponibilidad
from django.urls import path

from .views import lista_citas, crear_cita, editar_cita, cambiar_estado_cita, archivar_cita, restaurar_cita

app_name = "citas"

urlpatterns = [
    path("disponibilidad/", consultar_disponibilidad, name="disponibilidad"),
    path("<int:pk>/restaurar/", restaurar_cita, name="restaurar"),
    path("<int:pk>/archivar/", archivar_cita, name="archivar"),
    path("<int:pk>/estado/", cambiar_estado_cita, name="cambiar_estado"),
    path("", lista_citas, name="lista"),
    path("nueva/", crear_cita, name="nueva"),
    path("<int:pk>/editar/", editar_cita, name="editar"),
]
