from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import RegistroTutorForm
from tutores.models import Tutor


@require_http_methods(["GET", "POST"])
def registro_tutor(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        formulario = RegistroTutorForm(request.POST)

        if formulario.is_valid():
            datos = formulario.cleaned_data

            try:
                with transaction.atomic():
                    usuario = formulario.save(commit=False)

                    usuario.email = datos["correo"]
                    usuario.first_name = datos["nombre"]
                    usuario.last_name = datos["apellido"]

                    usuario.is_staff = False
                    usuario.is_superuser = False
                    usuario.is_active = True

                    usuario.save()
                    usuario.groups.clear()
                    usuario.user_permissions.clear()

                    Tutor.objects.create(
                        usuario=usuario,
                        rut=datos["rut"],
                        nombre=datos["nombre"],
                        apellido=datos["apellido"],
                        telefono=datos["telefono"],
                        correo=datos["correo"],
                        direccion=datos["direccion"],
                        activo=True,
                    )

            except IntegrityError:
                formulario.add_error(
                    None,
                    "No fue posible completar el registro. "
                    "Revise los datos e intente nuevamente."
                )
            else:
                login(
                    request,
                    usuario,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                return redirect("panel_tutor")

    else:
        formulario = RegistroTutorForm()

    return render(
        request,
        "registration/registro_tutor.html",
        {"form": formulario},
    )

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from citas.models import Cita  # PETCARE_CITAS_TUTOR_164F


@login_required(login_url="petcare_login")
def panel_tutor(request):
    usuario = request.user

    # El personal de la clinica utiliza su propio dashboard.
    if usuario.is_staff or usuario.is_superuser:
        return redirect("dashboard")

    # No permitir acceso mediante permisos administrativos.
    if usuario.groups.exists() or usuario.user_permissions.exists():
        raise PermissionDenied(
            "Esta cuenta requiere revision de permisos."
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        raise PermissionDenied(
            "No existe una ficha de tutor activa vinculada."
        )

    mascotas = tutor.mascotas.all()

    # Citas asociadas exclusivamente al tutor autenticado.
    citas_tutor = (
        Cita.objects.filter(
            mascota__tutor=tutor,
        )
        .select_related("mascota", "veterinario")
        .order_by("-fecha", "-hora_inicio")
    )[:20]

    # PETCARE_SOLICITUDES_119
    solicitudes = tutor.solicitudes_mascotas.all()



    # PETCARE_SOLICITUDES_CITAS_165Q2
    # Solo solicitudes del tutor autenticado.
    from citas.models import SolicitudCita

    solicitudes_citas = (
        SolicitudCita.objects.filter(tutor=tutor)
        .select_related("mascota", "cita")
        .order_by("-fecha_solicitud")[:20]
    )

    contexto = {
        "solicitudes_mascotas": solicitudes,

        "tutor": tutor,
        "mascotas": mascotas,
        "citas_tutor": citas_tutor,
        "solicitudes_citas": solicitudes_citas,
        "total_mascotas": mascotas.count(),
    }

    return render(
        request,
        "accounts/panel_tutor.html",
        contexto,
    )


# PETCARE_PASO_113_SOLICITAR_MASCOTA

from mascotas.forms import SolicitudMascotaForm
from django.views.decorators.http import require_http_methods


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def solicitar_mascota(request):

    usuario = request.user

    if usuario.is_staff or usuario.is_superuser:
        return redirect("dashboard")

    if usuario.groups.exists() or usuario.user_permissions.exists():
        raise PermissionDenied(
            "Esta cuenta requiere revision de permisos."
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        raise PermissionDenied(
            "No existe una ficha de tutor activa vinculada."
        )

    if request.method == "POST":
        formulario = SolicitudMascotaForm(request.POST)

        if formulario.is_valid():
            solicitud = formulario.save(commit=False)
            solicitud.tutor = tutor
            solicitud.estado = "PENDIENTE"
            solicitud.save()

            return redirect("panel_tutor")

    else:
        formulario = SolicitudMascotaForm()

    return render(
        request,
        "accounts/solicitar_mascota.html",
        {
            "formulario": formulario,
            "tutor": tutor,
        },
    )


# PETCARE_SOLICITAR_CITA_165K
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied

from citas.forms import SolicitudCitaForm
from tutores.models import Tutor


@login_required(login_url="petcare_login")
def solicitar_cita(request):
    usuario = request.user

    if (
        usuario.is_superuser
        or usuario.is_staff
        or usuario.groups.exists()
        or usuario.user_permissions.exists()
    ):
        raise PermissionDenied(
            "Esta funcionalidad es exclusiva para tutores."
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        raise PermissionDenied(
            "No existe un perfil de tutor activo."
        )

    if request.method == "POST":
        formulario = SolicitudCitaForm(
            request.POST,
            tutor=tutor,
        )

        if formulario.is_valid():
            formulario.save()

            messages.success(
                request,
                "Su solicitud de cita fue registrada "
                "y quedo pendiente de revision."
            )

            return redirect("panel_tutor")

    else:
        formulario = SolicitudCitaForm(
            tutor=tutor,
        )

    return render(
        request,
        "accounts/solicitar_cita.html",
        {
            "tutor": tutor,
            "formulario": formulario,
        },
    )


# PETCARE_HISTORIAL_TUTOR_165R6
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

@login_required(login_url="petcare_login")
def historial_mascota_tutor(request, mascota_id):
    from tutores.models import Tutor
    from mascotas.models import Mascota
    from historial_clinico.models import (
        FichaClinica,
        AtencionClinica,
        RecetaVeterinaria,
    )

    usuario = request.user

    if (
        not usuario.is_active
        or usuario.is_staff
        or usuario.is_superuser
        or usuario.groups.exists()
        or usuario.user_permissions.exists()
    ):
        raise PermissionDenied(
            "Acceso exclusivo para tutores."
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        raise PermissionDenied(
            "No existe un tutor activo vinculado."
        )

    mascota = get_object_or_404(
        Mascota.objects.filter(tutor=tutor),
        pk=mascota_id,
    )

    ficha = FichaClinica.objects.filter(
        mascota=mascota
    ).first()

    atenciones = AtencionClinica.objects.none()
    recetas = RecetaVeterinaria.objects.none()

    if ficha is not None:
        atenciones = (
            AtencionClinica.objects
            .filter(ficha=ficha)
            .select_related("veterinario", "cita")
            .order_by("-fecha_atencion", "-pk")
        )

        recetas = (
            RecetaVeterinaria.objects
            .filter(atencion__ficha=ficha)
            .select_related("atencion")
            .prefetch_related("medicamentos")
            .order_by("-fecha_emision", "-pk")
        )

    return render(
        request,
        "accounts/historial_mascota_tutor.html",
        {
            "tutor": tutor,
            "mascota": mascota,
            "ficha": ficha,
            "atenciones": atenciones,
            "recetas": recetas,
        },
    )



# PETCARE_GESTION_SOLICITUDES_165R23
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from citas.forms import EditarSolicitudCitaForm
from citas.models import SolicitudCita
from tutores.models import Tutor


def _tutor_gestion_solicitudes(request):
    usuario = request.user

    if (
        usuario.is_superuser
        or usuario.is_staff
        or usuario.groups.exists()
        or usuario.user_permissions.exists()
    ):
        raise PermissionDenied(
            "Esta funcionalidad es exclusiva para tutores."
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        raise PermissionDenied(
            "No existe un perfil de tutor activo."
        )

    return tutor


@login_required(login_url="petcare_login")
def editar_solicitud_cita(request, solicitud_id):
    tutor = _tutor_gestion_solicitudes(request)

    if request.method == "POST":
        with transaction.atomic():
            solicitud = get_object_or_404(
                SolicitudCita.objects.select_for_update(),
                pk=solicitud_id,
                tutor=tutor,
                estado=SolicitudCita.Estado.PENDIENTE,
                cita__isnull=True,
            )

            formulario = EditarSolicitudCitaForm(
                request.POST,
                instance=solicitud,
                tutor=tutor,
            )

            if formulario.is_valid():
                formulario.save()
                messages.success(
                    request,
                    "La solicitud fue actualizada correctamente."
                )
                return redirect("panel_tutor")
    else:
        solicitud = get_object_or_404(
            SolicitudCita,
            pk=solicitud_id,
            tutor=tutor,
            estado=SolicitudCita.Estado.PENDIENTE,
            cita__isnull=True,
        )

        formulario = EditarSolicitudCitaForm(
            instance=solicitud,
            tutor=tutor,
        )

    return render(
        request,
        "accounts/editar_solicitud_cita.html",
        {
            "tutor": tutor,
            "solicitud": solicitud,
            "formulario": formulario,
        },
    )


@login_required(login_url="petcare_login")
@require_POST
def cancelar_solicitud_cita(request, solicitud_id):
    tutor = _tutor_gestion_solicitudes(request)

    with transaction.atomic():
        solicitud = get_object_or_404(
            SolicitudCita.objects.select_for_update(),
            pk=solicitud_id,
            tutor=tutor,
            estado=SolicitudCita.Estado.PENDIENTE,
            cita__isnull=True,
        )

        solicitud.estado = SolicitudCita.Estado.CANCELADA
        solicitud.save(update_fields=["estado"])

    messages.success(
        request,
        "La solicitud fue cancelada correctamente."
    )

    return redirect("panel_tutor")
