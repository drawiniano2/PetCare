from django.urls import path

from .views import panel_tutor, registro_tutor, solicitar_mascota, solicitar_cita


urlpatterns = [
    path(
        "solicitar-cita/",
        solicitar_cita,
        name="solicitar_cita",
    ),

    path(
        "solicitar-mascota/",
        solicitar_mascota,
        name="solicitar_mascota",
    ),
    path(
        "registro/",
        registro_tutor,
        name="registro_tutor",
    ),

    path(
        "mi-panel/",
        panel_tutor,
        name="panel_tutor",
    ),
]


# PETCARE_HISTORIAL_TUTOR_165R7
from .views import historial_mascota_tutor

urlpatterns += [
    path(
        "mi-panel/mascotas/<int:mascota_id>/historial/",
        historial_mascota_tutor,
        name="historial_mascota_tutor",
    ),
]


# PETCARE_RUTAS_SOLICITUDES_165R24
from .views import editar_solicitud_cita, cancelar_solicitud_cita


# PETCARE_RUTAS_SOLICITUDES_165R24
urlpatterns += [
    path(
        "solicitudes-citas/<int:solicitud_id>/editar/",
        editar_solicitud_cita,
        name="editar_solicitud_cita",
    ),
    path(
        "solicitudes-citas/<int:solicitud_id>/cancelar/",
        cancelar_solicitud_cita,
        name="cancelar_solicitud_cita",
    ),
]
