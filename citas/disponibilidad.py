from datetime import datetime, timedelta

from django.utils import timezone

from horarios.models import Horario

from .models import Cita


def obtener_horas_disponibles(
    veterinario_id,
    fecha,
    duracion_minutos=30,
    excluir_cita_id=None,
):
    """
    Devuelve horas de inicio disponibles en formato HH:MM.
    Considera horarios activos, duración y citas existentes.
    """
    if not veterinario_id or not fecha:
        return []

    try:
        duracion_minutos = int(duracion_minutos)
        if duracion_minutos <= 0 or duracion_minutos > 1440:
            return []
    except (TypeError, ValueError):
        return []

    horarios = Horario.objects.filter(
        veterinario_id=veterinario_id,
        dia_semana=fecha.weekday(),
        activo=True,
    ).order_by("hora_inicio")

    citas = Cita.objects.filter(
        veterinario_id=veterinario_id,
        fecha=fecha,
    ).exclude(
        estado=Cita.Estado.CANCELADA,
    )

    if excluir_cita_id:
        citas = citas.exclude(pk=excluir_cita_id)

    ocupados = []
    for cita in citas:
        inicio = datetime.combine(fecha, cita.hora_inicio)
        fin = inicio + timedelta(minutes=cita.duracion_minutos)
        ocupados.append((inicio, fin))

    ahora = timezone.localtime()
    disponibles = []

    for horario in horarios:
        inicio = datetime.combine(fecha, horario.hora_inicio)
        termino = datetime.combine(fecha, horario.hora_fin)

        while inicio + timedelta(minutes=duracion_minutos) <= termino:
            fin = inicio + timedelta(minutes=duracion_minutos)

            if fecha < ahora.date() or (
                fecha == ahora.date()
                and inicio.time() <= ahora.time()
            ):
                inicio += timedelta(minutes=30)
                continue

            conflicto = any(
                inicio < fin_ocupado and fin > inicio_ocupado
                for inicio_ocupado, fin_ocupado in ocupados
            )

            if not conflicto:
                disponibles.append(inicio.strftime("%H:%M"))

            inicio += timedelta(minutes=30)

    return sorted(set(disponibles))
