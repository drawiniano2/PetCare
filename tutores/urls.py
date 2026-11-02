from django.urls import path

from .views import lista_tutores, crear_tutor, editar_tutor, detalle_tutor

app_name = "tutores"

urlpatterns = [
    path("", lista_tutores, name="lista"),
    path("nuevo/", crear_tutor, name="crear"),
    path("<int:pk>/editar/", editar_tutor, name="editar"),
    path("<int:pk>/", detalle_tutor, name="detalle"),
]

