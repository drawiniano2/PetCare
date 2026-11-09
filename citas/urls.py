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


# PETCARE 165R.353.4
from .panel_solicitudes import solicitudes_lista, solicitudes_detalle

urlpatterns += [
    path("solicitudes/", solicitudes_lista, name="solicitudes_lista"),
    path(
        "solicitudes/<int:pk>/",
        solicitudes_detalle,
        name="solicitudes_detalle",
    ),
]

# PETCARE 165R.357.9.223 - PERSONAL ESTETICA
from .personal_estetica import (
    lista_personal,
    crear_personal,
    editar_personal,
    cambiar_activo_personal,
)

urlpatterns += [
    path(
        "personal-estetica/",
        lista_personal,
        name="personal_estetica",
    ),
    path(
        "personal-estetica/nuevo/",
        crear_personal,
        name="personal_estetica_nuevo",
    ),
    path(
        "personal-estetica/<int:pk>/editar/",
        editar_personal,
        name="personal_estetica_editar",
    ),
    path(
        "personal-estetica/<int:pk>/estado/",
        cambiar_activo_personal,
        name="personal_estetica_estado",
    ),
]

# PETCARE 165R.357.9.227 - HORARIOS ESTETICA
from .horarios_estetica import (
    lista_horarios,
    crear_horario,
    editar_horario,
    cambiar_estado_horario,
)

urlpatterns += [
    path(
        "horarios-estetica/",
        lista_horarios,
        name="horarios_estetica",
    ),
    path(
        "horarios-estetica/nuevo/",
        crear_horario,
        name="horarios_estetica_nuevo",
    ),
    path(
        "horarios-estetica/<int:pk>/editar/",
        editar_horario,
        name="horarios_estetica_editar",
    ),
    path(
        "horarios-estetica/<int:pk>/estado/",
        cambiar_estado_horario,
        name="horarios_estetica_estado",
    ),
]


# PETCARE 165R.357.9.234 - RUTA CATALOGO
from .catalogo_servicios import lista_servicios

urlpatterns += [
    path(
        "catalogo-servicios/",
        lista_servicios,
        name="catalogo_servicios",
    ),
]


# PETCARE 165R.357.9.235 - ADMINISTRACION CATALOGO
from .catalogo_servicios import (
    crear_servicio,
    editar_servicio,
    cambiar_estado_servicio,
)

urlpatterns += [
    path(
        "catalogo-servicios/nuevo/",
        crear_servicio,
        name="catalogo_servicios_nuevo",
    ),
    path(
        "catalogo-servicios/<int:pk>/editar/",
        editar_servicio,
        name="catalogo_servicios_editar",
    ),
    path(
        "catalogo-servicios/<int:pk>/estado/",
        cambiar_estado_servicio,
        name="catalogo_servicios_estado",
    ),
]
