# PETCARE 165R.353.4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import SolicitudCita
from .forms_gestion import (
    AprobarSolicitudCitaForm,
    RechazarSolicitudCitaForm,
)
from .gestion_solicitudes import (
    aprobar_solicitud,
    rechazar_solicitud,
)


def _verificar_permiso(request, modificar=False):
    usuario = request.user
    if not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied

    permiso = (
        "citas.change_solicitudcita"
        if modificar else "citas.view_solicitudcita"
    )

    if not usuario.is_superuser and not usuario.has_perm(permiso):
        raise PermissionDenied


@login_required
def solicitudes_lista(request):
    _verificar_permiso(request)

    solicitudes = SolicitudCita.objects.select_related(
        "tutor", "mascota", "veterinario_preferido", "cita"
    ).order_by("-fecha_solicitud", "-pk")

    estado = request.GET.get("estado", "")
    if estado in SolicitudCita.Estado.values:
        solicitudes = solicitudes.filter(estado=estado)

    pagina = Paginator(solicitudes, 15).get_page(
        request.GET.get("page")
    )

    return render(request, "citas/panel_solicitudes_lista.html", {
        "pagina": pagina,
        "estado_actual": estado,
        "estados": SolicitudCita.Estado.choices,
    })


@login_required
@require_http_methods(["GET", "POST"])
def solicitudes_detalle(request, pk):
    _verificar_permiso(request)

    solicitud = get_object_or_404(
        SolicitudCita.objects.select_related(
            "tutor", "mascota", "veterinario_preferido", "cita"
        ),
        pk=pk,
    )

    inicial = {}
    if (
        solicitud.veterinario_preferido
        and solicitud.veterinario_preferido.activo
    ):
        inicial["veterinario"] = solicitud.veterinario_preferido.pk

    formulario_aprobar = AprobarSolicitudCitaForm(initial=inicial)
    formulario_rechazar = RechazarSolicitudCitaForm()

    if request.method == "POST":
        _verificar_permiso(request, modificar=True)

        if (
            solicitud.estado != SolicitudCita.Estado.PENDIENTE
            or solicitud.cita_id is not None
        ):
            messages.error(request, "La solicitud ya fue gestionada.")
            return redirect("citas:solicitudes_detalle", pk=pk)

        accion = request.POST.get("accion")

        if accion == "aprobar":
            formulario_aprobar = AprobarSolicitudCitaForm(request.POST)
            if formulario_aprobar.is_valid():
                datos = formulario_aprobar.cleaned_data
                try:
                    cita = aprobar_solicitud(
                        solicitud.pk,
                        datos["veterinario"].pk,
                        datos["duracion_minutos"],
                        datos["observaciones_clinica"],
                    )
                except (ValidationError, ValueError) as error:
                    messages.error(request, str(error))
                else:
                    messages.success(
                        request,
                        f"Solicitud aprobada. Cita N.º {cita.pk} creada."
                    )
                    return redirect("citas:solicitudes_detalle", pk=pk)

        elif accion == "rechazar":
            formulario_rechazar = RechazarSolicitudCitaForm(request.POST)
            if formulario_rechazar.is_valid():
                try:
                    rechazar_solicitud(
                        solicitud.pk,
                        formulario_rechazar.cleaned_data[
                            "observaciones_clinica"
                        ],
                    )
                except ValidationError as error:
                    messages.error(request, str(error))
                else:
                    messages.success(
                        request,
                        "Solicitud rechazada correctamente."
                    )
                    return redirect("citas:solicitudes_detalle", pk=pk)
        else:
            messages.error(request, "Acción no reconocida.")

    puede_gestionar = (
        request.user.is_superuser
        or request.user.has_perm("citas.change_solicitudcita")
    )

    return render(request, "citas/panel_solicitudes_detalle.html", {
        "solicitud": solicitud,
        "formulario_aprobar": formulario_aprobar,
        "formulario_rechazar": formulario_rechazar,
        "puede_gestionar": puede_gestionar,
    })
