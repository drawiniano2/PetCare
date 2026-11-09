from django.core.exceptions import PermissionDenied

from historial_clinico.views import (
    _perfil_clinico_usuario,
    mascotas_clinicas_visibles,
)
from historial_clinico.models import FichaClinica
from veterinarios.models import Veterinario


def perfil_usuario(usuario):
    return _perfil_clinico_usuario(usuario)


def fichas_visibles(usuario):
    pacientes = mascotas_clinicas_visibles(usuario)
    return FichaClinica.objects.filter(mascota__in=pacientes)


def veterinarios_asignables(usuario):
    perfil = perfil_usuario(usuario)

    if perfil == "ADMINISTRADOR":
        return Veterinario.objects.filter(activo=True)

    if perfil == "VETERINARIO":
        return Veterinario.objects.filter(
            usuario=usuario,
            activo=True,
        )

    return Veterinario.objects.none()


def exigir_gestion(usuario):
    if perfil_usuario(usuario) not in (
        "ADMINISTRADOR",
        "VETERINARIO",
    ):
        raise PermissionDenied
