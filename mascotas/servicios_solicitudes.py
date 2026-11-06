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


@transaction.atomic
def aprobar_vinculacion_mascota(
    solicitud_id,
    usuario,
    mascota_id,
    observacion,
    titularidad_verificada=False,
    tutor_actual_id_confirmado=None,
):
    verificar_revisor(usuario)

    if not titularidad_verificada:
        raise ValidationError(
            "Debe confirmar la verificacion de titularidad."
        )

    observacion = (observacion or "").strip()

    if not observacion:
        raise ValidationError(
            "Debe registrar el antecedente que autoriza la transferencia."
        )

    solicitud = SolicitudMascota.objects.select_for_update().get(
        pk=solicitud_id
    )

    validar_solicitud_pendiente(solicitud)

    if solicitud.tipo != SolicitudMascota.Tipo.VINCULAR:
        raise ValidationError(
            "La solicitud no corresponde a una vinculacion."
        )

    try:
        mascota = Mascota.objects.select_for_update().get(
            pk=mascota_id
        )
    except (Mascota.DoesNotExist, ValueError, TypeError):
        raise ValidationError(
            "La mascota seleccionada no existe."
        )

    if not mascota.activo:
        raise ValidationError(
            "La mascota seleccionada no esta activa."
        )

    if mascota.tutor_id == solicitud.tutor_id:
        raise ValidationError(
            "La mascota ya pertenece al tutor solicitante."
        )

    if mascota.nombre.strip().casefold() != solicitud.nombre.strip().casefold():
        raise ValidationError(
            "El nombre de la mascota no coincide."
        )

    if mascota.especie != solicitud.especie:
        raise ValidationError(
            "La especie de la mascota no coincide."
        )

    if mascota.sexo != solicitud.sexo:
        raise ValidationError(
            "El sexo de la mascota no coincide."
        )

    microchip_solicitud = normalizar_microchip(solicitud.microchip)
    microchip_mascota = normalizar_microchip(mascota.microchip)

    if microchip_solicitud:
        if (
            not microchip_mascota
            or microchip_solicitud.casefold() != microchip_mascota.casefold()
        ):
            raise ValidationError(
                "El microchip no coincide con la mascota existente."
            )

    tutor_anterior_id = mascota.tutor_id

    if str(tutor_actual_id_confirmado or "").strip() != str(tutor_anterior_id):
        raise ValidationError(
            "El ID del tutor actual no coincide. "
            "Verifique los antecedentes antes de transferir."
        )

    mascota.tutor = solicitud.tutor
    mascota.full_clean()
    mascota.save(update_fields=["tutor"])

    solicitud.estado = SolicitudMascota.Estado.APROBADA
    solicitud.revisado_por = usuario
    solicitud.fecha_revision = timezone.now()
    solicitud.observacion_revision = (
        f"Transferencia autorizada. Mascota ID: {mascota.pk}. "
        f"Tutor anterior ID: {tutor_anterior_id}. "
        f"Tutor nuevo ID: {solicitud.tutor_id}. "
        f"Antecedente: {observacion}"
    )

    solicitud.save(
        update_fields=[
            "estado",
            "revisado_por",
            "fecha_revision",
            "observacion_revision",
        ]
    )

    return solicitud, mascota
