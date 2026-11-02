from django.urls import path

from .views import lista_veterinarios, crear_veterinario, detalle_veterinario, editar_veterinario

app_name = "veterinarios"

urlpatterns = [
    path("", lista_veterinarios, name="lista"),
    path("nuevo/", crear_veterinario, name="nuevo"),
    path("<int:pk>/", detalle_veterinario, name="detalle"),
    path("<int:pk>/editar/", editar_veterinario, name="editar"),
]
