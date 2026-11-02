from django.core.exceptions import ValidationError
from django.db import transaction

from citas.models import Cita, SolicitudCita
from veterinarios.models import Veterinario


def _obtener_solicitud_pendiente(solicitud_id):
    solicitud = (
        SolicitudCita.objects
        .select_for_update()
        .get(pk=solicitud_id)
    )

    if (
        solicitud.estado != SolicitudCita.Estado.PENDIENTE
        or solicitud.cita_id is not None
    ):
        raise ValidationError(
            "Esta solicitud ya no esta disponible "
            "para su gestion."
        )

    return solicitud


@transaction.atomic
def aprobar_solicitud(
    solicitud_id,
    veterinario_id,
    duracion_minutos=30,
    observaciones="",
):
    solicitud = _obtener_solicitud_pendiente(
        solicitud_id
    )

    veterinario = (
        Veterinario.objects
        .select_for_update()
        .get(pk=veterinario_id)
    )

    if not veterinario.activo:
        raise ValidationError(
            "El veterinario seleccionado no esta activo."
        )

    cita = Cita(
        mascota=solicitud.mascota,
        veterinario=veterinario,
        fecha=solicitud.fecha_preferida,
        hora_inicio=solicitud.hora_preferida,
        duracion_minutos=duracion_minutos,
        motivo=solicitud.motivo,
        estado=Cita.Estado.PROGRAMADA,
    )

    cita.save()

    solicitud.cita = cita
    solicitud.estado = SolicitudCita.Estado.APROBADA
    solicitud.observaciones_clinica = (
        observaciones or ""
    ).strip()

    solicitud.save(
        update_fields=[
            "cita",
            "estado",
            "observaciones_clinica",
        ]
    )

    return cita


@transaction.atomic
def rechazar_solicitud(
    solicitud_id,
    motivo,
):
    solicitud = _obtener_solicitud_pendiente(
        solicitud_id
    )

    motivo = (motivo or "").strip()

    if len(motivo) < 5:
        raise ValidationError(
            "Debe indicar un motivo de rechazo "
            "de al menos 5 caracteres."
        )

    solicitud.estado = SolicitudCita.Estado.RECHAZADA
    solicitud.observaciones_clinica = motivo

    solicitud.save(
        update_fields=[
            "estado",
            "observaciones_clinica",
        ]
    )

    return solicitud
