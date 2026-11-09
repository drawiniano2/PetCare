from django.urls import path

from .views import panel_tutor, registro_tutor, solicitar_mascota, solicitar_cita


from .views import disponibilidad_tutor

urlpatterns = [
    path(
        "disponibilidad-tutor/",
        disponibilidad_tutor,
        name="disponibilidad_tutor",
    ),
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


# PETCARE_RUTA_SOLICITUD_ACCESO_165R359
from .views import solicitar_acceso

urlpatterns += [
    path(
        "solicitar-acceso/",
        solicitar_acceso,
        name="solicitar_acceso",
    ),
]


# PETCARE_CAMBIO_PASSWORD_165R426
from .views import cambiar_password_obligatorio

urlpatterns += [
    path(
        "cambiar-password-obligatorio/",
        cambiar_password_obligatorio,
        name="cambiar_password_obligatorio",
    ),
]


# PETCARE_LISTADO_ACCESOS_165R323
from .views import solicitudes_acceso_lista

urlpatterns += [
    path(
        "solicitudes-acceso/",
        solicitudes_acceso_lista,
        name="solicitudes_acceso_lista",
    ),
]


# PETCARE_REVISION_ACCESOS_165R324
from .views import solicitudes_acceso_revisar

urlpatterns += [
    path(
        "solicitudes-acceso/<int:solicitud_id>/revisar/",
        solicitudes_acceso_revisar,
        name="solicitudes_acceso_revisar",
    ),
]


# PETCARE_PANTALLA_ACTIVACION_165R3277
from .views import solicitudes_acceso_activar

urlpatterns += [
    path(
        "solicitudes-acceso/<int:solicitud_id>/activar/",
        solicitudes_acceso_activar,
        name="solicitudes_acceso_activar",
    ),
]
