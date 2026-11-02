from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from tutores.models import Tutor
from mascotas.models import Mascota, SolicitudMascota
from veterinarios.models import Veterinario
from citas.models import Cita
from citas.views import citas_visibles_para_usuario
from historial_clinico.models import FichaClinica, AtencionClinica
from historial_clinico.views import (
    mascotas_clinicas_visibles,
    atenciones_clinicas_visibles,
)


@login_required(login_url="petcare_login")
def dashboard(request):
    usuario = request.user

    # Las cuentas publicas de tutores utilizan su panel privado.
    if not usuario.is_staff and not usuario.is_superuser:
        return redirect("panel_tutor")

    hoy = timezone.localdate()

    grupos = set(usuario.groups.values_list("name", flat=True))

    es_admin = usuario.is_superuser or "Administrador" in grupos
    es_recepcion = "Recepcionista" in grupos
    es_veterinario = "Veterinario" in grupos

    acceso_administrativo = es_admin or es_recepcion
    acceso_clinico = es_admin or es_veterinario

    citas = citas_visibles_para_usuario(usuario)

    if not (acceso_administrativo or es_veterinario):
        citas = Cita.objects.none()

    if acceso_administrativo:
        total_tutores = Tutor.objects.count()
        total_mascotas = Mascota.objects.count()
        total_veterinarios = Veterinario.objects.count()
    elif es_veterinario:
        pacientes = mascotas_clinicas_visibles(usuario)
        total_tutores = pacientes.values("tutor_id").distinct().count()
        total_mascotas = pacientes.count()
        total_veterinarios = 1 if Veterinario.objects.filter(
            usuario=usuario, activo=True
        ).exists() else 0
    else:
        total_tutores = 0
        total_mascotas = 0
        total_veterinarios = 0

    proximas_citas = (
        citas.filter(
            fecha__gte=hoy,
            estado__in=["PROGRAMADA", "CONFIRMADA"],
        )
        .select_related("mascota", "veterinario")
        .order_by("fecha", "hora_inicio")[:10]
    )

    # PETCARE_PASO_152_SOLICITUDES
    puede_ver_solicitudes = (
        usuario.is_active
        and usuario.is_staff
        and usuario.has_perm("mascotas.view_solicitudmascota")
    )

    solicitudes_pendientes = None

    if puede_ver_solicitudes:
        solicitudes_pendientes = SolicitudMascota.objects.filter(
            estado=SolicitudMascota.Estado.PENDIENTE
        ).count()

    contexto = {
        "puede_ver_solicitudes": puede_ver_solicitudes,
        "solicitudes_pendientes": solicitudes_pendientes,
        "total_tutores": total_tutores,
        "total_mascotas": total_mascotas,
        "total_veterinarios": total_veterinarios,
        "total_citas_programadas": citas.filter(
            estado="PROGRAMADA"
        ).count(),
        "total_citas_completadas": citas.filter(
            estado="COMPLETADA"
        ).count(),
        "total_citas_canceladas": citas.filter(
            estado="CANCELADA"
        ).count(),
        "proximas_citas": proximas_citas,
        "total_fichas": None,
        "total_atenciones": None,
    }

    if acceso_clinico and usuario.has_perm(
        "historial_clinico.view_fichaclinica"
    ):
        if es_admin:
            contexto["total_fichas"] = FichaClinica.objects.count()
        else:
            contexto["total_fichas"] = FichaClinica.objects.filter(
                mascota__in=mascotas_clinicas_visibles(usuario)
            ).count()

    if acceso_clinico and usuario.has_perm(
        "historial_clinico.view_atencionclinica"
    ):
        contexto["total_atenciones"] = (
            atenciones_clinicas_visibles(usuario).count()
        )

    return render(request, "dashboard/inicio.html", contexto)
