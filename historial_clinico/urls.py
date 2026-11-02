from django.urls import path

from .views import lista_historiales, detalle_ficha, nueva_atencion, detalle_atencion, editar_atencion, nueva_receta, detalle_receta

app_name = "historial_clinico"


urlpatterns = [

    # PETCARE V20 - DETALLE DE RECETA VETERINARIA
    path(
        "<int:mascota_id>/atenciones/<int:atencion_id>/recetas/<int:receta_id>/",
        detalle_receta,
        name="detalle_receta",
    ),

    # PETCARE V20 - NUEVA RECETA
    path(
        "<int:mascota_id>/atenciones/<int:atencion_id>/nueva-receta/",
        nueva_receta,
        name="nueva_receta",
    ),

    # PETCARE V19 - RUTA DE EDICION
    path(
        "<int:mascota_id>/atenciones/<int:atencion_id>/editar/",
        editar_atencion,
        name="editar_atencion",
    ),
    path("<int:mascota_id>/nueva-atencion/", nueva_atencion, name="nueva_atencion"),
    path("<int:mascota_id>/atenciones/<int:atencion_id>/", detalle_atencion, name="detalle_atencion"),
    path("", lista_historiales, name="lista"),
    path("<int:mascota_id>/", detalle_ficha, name="detalle"),
]
