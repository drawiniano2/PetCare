# PETCARE_PASO_146_SERVICIO_REVISION
# Logica de revision de solicitudes de mascotas.

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import Mascota, SolicitudMascota


def verificar_revisor(usuario):
    if not getattr(usuario, "is_authenticated", False):
        raise PermissionDenied("Debe iniciar sesion.")

    if not usuario.is_active:
        raise PermissionDenied("Usuario inactivo.")

    if not usuario.is_staff:
        raise PermissionDenied("Se requiere personal autorizado.")

    if not usuario.has_perm("mascotas.change_solicitudmascota"):
        raise PermissionDenied("No tiene permiso para revisar solicitudes.")


def validar_solicitud_pendiente(solicitud):
    if solicitud.estado != SolicitudMascota.Estado.PENDIENTE:
        raise ValidationError(
            "La solicitud ya fue revisada."
        )


def normalizar_microchip(valor):
    valor = (valor or "").strip()
    return valor or None


def validar_mascota_nueva(solicitud):
    if solicitud.tipo != SolicitudMascota.Tipo.NUEVA:
        raise ValidationError(
            "Esta solicitud no corresponde a una mascota nueva."
        )

    nombre = (solicitud.nombre or "").strip()

    if not nombre:
        raise ValidationError(
            "La mascota debe tener un nombre."
        )

    especies = {
        valor for valor, _ in Mascota.Especie.choices
    }

    sexos = {
        valor for valor, _ in Mascota.Sexo.choices
    }

    if solicitud.especie not in especies:
        raise ValidationError("Especie no valida.")

    if solicitud.sexo not in sexos:
        raise ValidationError("Sexo no valido.")

    microchip = normalizar_microchip(solicitud.microchip)

    if microchip and Mascota.objects.filter(
        microchip__iexact=microchip
    ).exists():
        raise ValidationError(
            "Ya existe una mascota con ese microchip."
        )

    return microchip


@transaction.atomic
def rechazar_solicitud(solicitud_id, usuario, motivo):
    verificar_revisor(usuario)

    motivo = (motivo or "").strip()

    if not motivo:
        raise ValidationError(
            "Debe indicar el motivo del rechazo."
        )

    solicitud = SolicitudMascota.objects.select_for_update().get(
        pk=solicitud_id
    )

    validar_solicitud_pendiente(solicitud)

    solicitud.estado = SolicitudMascota.Estado.RECHAZADA
    solicitud.revisado_por = usuario
    solicitud.fecha_revision = timezone.now()
    solicitud.observacion_revision = motivo

    solicitud.save(
        update_fields=[
            "estado",
            "revisado_por",
            "fecha_revision",
            "observacion_revision",
        ]
    )

    return solicitud


@transaction.atomic
def aprobar_mascota_nueva(solicitud_id, usuario, observacion=""):
    verificar_revisor(usuario)

    solicitud = SolicitudMascota.objects.select_for_update().get(
        pk=solicitud_id
    )

    validar_solicitud_pendiente(solicitud)
    microchip = validar_mascota_nueva(solicitud)

    mascota = Mascota(
        tutor=solicitud.tutor,
        nombre=solicitud.nombre.strip(),
        especie=solicitud.especie,
        raza=solicitud.raza,
        sexo=solicitud.sexo,
        microchip=microchip,
    )

    mascota.full_clean()
    mascota.save()

    solicitud.estado = SolicitudMascota.Estado.APROBADA
    solicitud.revisado_por = usuario
    solicitud.fecha_revision = timezone.now()
    solicitud.observacion_revision = (observacion or "").strip()

    solicitud.save(
        update_fields=[
            "estado",
            "revisado_por",
            "fecha_revision",
            "observacion_revision",
        ]
    )

    return solicitud, mascota
