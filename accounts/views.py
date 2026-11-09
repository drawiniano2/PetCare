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


# PETCARE_VISTA_SOLICITUD_ACCESO_165R356

from accounts.forms import SolicitudAccesoForm


@require_http_methods(["GET", "POST"])
def solicitar_acceso(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        formulario = SolicitudAccesoForm(request.POST)

        if formulario.is_valid():
            formulario.save()

            return render(
                request,
                "registration/solicitud_acceso_confirmada.html",
                status=200,
            )
    else:
        formulario = SolicitudAccesoForm()

    return render(
        request,
        "registration/solicitar_acceso.html",
        {"form": formulario},
    )


# PETCARE_CAMBIO_PASSWORD_165R426
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from accounts.models import SolicitudAcceso


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def cambiar_password_obligatorio(request):
    solicitud = SolicitudAcceso.objects.filter(
        usuario_creado=request.user,
        estado=SolicitudAcceso.Estado.APROBADA,
        cambio_password_obligatorio=True,
    ).first()

    if solicitud is None:
        raise PermissionDenied(
            "No existe un cambio obligatorio pendiente."
        )

    if request.method == "POST":
        formulario = PasswordChangeForm(
            request.user,
            request.POST,
        )

        if formulario.is_valid():
            usuario = formulario.save()
            update_session_auth_hash(request, usuario)

            solicitud.cambio_password_obligatorio = False
            solicitud.save(
                update_fields=["cambio_password_obligatorio"]
            )

            return redirect("dashboard")
    else:
        formulario = PasswordChangeForm(request.user)

    return render(
        request,
        "registration/cambiar_password_obligatorio.html",
        {"formulario": formulario},
    )


# PETCARE_LISTADO_ACCESOS_165R323
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import SolicitudAcceso


@login_required(login_url="petcare_login")
def solicitudes_acceso_lista(request):
    if not request.user.is_active or not request.user.is_superuser:
        raise PermissionDenied

    solicitudes = SolicitudAcceso.objects.all()

    busqueda = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    if busqueda:
        solicitudes = solicitudes.filter(
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
            | Q(rut__icontains=busqueda)
            | Q(correo__icontains=busqueda)
            | Q(username_solicitado__icontains=busqueda)
        )

    estados_validos = {
        valor for valor, etiqueta in SolicitudAcceso.Estado.choices
    }
    tipos_validos = {
        valor for valor, etiqueta in SolicitudAcceso.TipoCuenta.choices
    }

    if estado in estados_validos:
        solicitudes = solicitudes.filter(estado=estado)

    if tipo in tipos_validos:
        solicitudes = solicitudes.filter(tipo_cuenta=tipo)

    solicitudes = solicitudes.order_by("-fecha_solicitud", "-pk")

    pagina = Paginator(solicitudes, 10).get_page(
        request.GET.get("page")
    )

    contexto = {
        "solicitudes": pagina,
        "busqueda": busqueda,
        "estado": estado,
        "tipo": tipo,
        "total": solicitudes.count(),
        "pendientes": SolicitudAcceso.objects.filter(
            estado=SolicitudAcceso.Estado.PENDIENTE
        ).count(),
        "aprobadas": SolicitudAcceso.objects.filter(
            estado=SolicitudAcceso.Estado.APROBADA
        ).count(),
        "rechazadas": SolicitudAcceso.objects.filter(
            estado=SolicitudAcceso.Estado.RECHAZADA
        ).count(),
    }

    return render(
        request,
        "accounts/solicitudes_acceso_lista.html",
        contexto,
    )


# PETCARE_REVISION_ACCESOS_165R324
from django.shortcuts import get_object_or_404


@login_required(login_url="petcare_login")
def solicitudes_acceso_revisar(request, solicitud_id):
    # PETCARE_APROBACION_PANEL_165R325
    from accounts.admin import (
        AprobacionSolicitudForm,
        aprobar_solicitud_acceso,
    )
    from django.contrib import messages
    from django.core.exceptions import ValidationError
    from django.shortcuts import redirect

    if not request.user.is_active or not request.user.is_superuser:
        raise PermissionDenied

    solicitud = get_object_or_404(
        SolicitudAcceso.objects.select_related(
            "revisado_por",
            "usuario_creado",
        ),
        pk=solicitud_id,
    )

    formulario = None
    error_rechazo = None

    # PETCARE_RECHAZO_NATIVO_165R3262
    if request.method == "POST" and request.POST.get("accion") == "rechazar":
        from django.db import transaction
        from django.utils import timezone
        from django.contrib import messages
        from django.shortcuts import redirect

        motivo = request.POST.get("motivo_rechazo", "").strip()

        if not motivo:
            error_rechazo = "Debe indicar el motivo del rechazo."
        elif len(motivo) > 5000:
            error_rechazo = "El motivo no puede superar 5000 caracteres."
        else:
            with transaction.atomic():
                actual = get_object_or_404(
                    SolicitudAcceso.objects.select_for_update(),
                    pk=solicitud_id,
                )

                if actual.estado != SolicitudAcceso.Estado.PENDIENTE:
                    error_rechazo = "Esta solicitud ya fue revisada."
                elif actual.usuario_creado_id:
                    error_rechazo = (
                        "No se puede rechazar una solicitud "
                        "que ya tiene una cuenta asociada."
                    )
                else:
                    actual.estado = SolicitudAcceso.Estado.RECHAZADA
                    actual.observaciones = motivo
                    actual.revisado_por = request.user
                    actual.fecha_revision = timezone.now()
                    actual.save(update_fields=[
                        "estado",
                        "observaciones",
                        "revisado_por",
                        "fecha_revision",
                    ])

            if error_rechazo is None:
                messages.success(
                    request,
                    "Solicitud rechazada y revisión registrada.",
                )
                return redirect(
                    "solicitudes_acceso_revisar",
                    solicitud_id,
                )

    if solicitud.estado == SolicitudAcceso.Estado.PENDIENTE:
        formulario = AprobacionSolicitudForm(
            request.POST if request.method == "POST" else None,
            solicitud=solicitud,
        )

        if (
            request.method == "POST"
            and request.POST.get("accion") == "aprobar"  # PETCARE_ACCIONES_SEGURAS_165R3274
            and formulario.is_valid()
        ):
            ficha = formulario.cleaned_data.get("ficha_veterinaria")

            try:
                aprobar_solicitud_acceso(
                    solicitud_id=solicitud.pk,
                    administrador=request.user,
                    identidad_verificada=formulario.cleaned_data[
                        "identidad_verificada"
                    ],
                    ficha_veterinaria_id=(
                        ficha.pk if ficha is not None else None
                    ),
                )
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                messages.success(
                    request,
                    "Solicitud aprobada correctamente. "
                    "La cuenta fue creada inactiva y sin contraseña.",
                )
                return redirect(
                    "solicitudes_acceso_revisar",
                    solicitud.pk,
                )

    # PETCARE_FICHA_DISPONIBLE_165R32515
    ficha_disponible = True

    if (
        formulario is not None
        and solicitud.tipo_cuenta == SolicitudAcceso.TipoCuenta.VETERINARIO
    ):
        ficha_disponible = (
            formulario.fields["ficha_veterinaria"]
            .queryset.exists()
        )

    return render(
        request,
        "accounts/solicitudes_acceso_revisar.html",
        {
            "solicitud": solicitud,
            "formulario_aprobacion": formulario,
            "ficha_disponible": ficha_disponible,
            "error_rechazo": error_rechazo,
        },
    )


# PETCARE_ACTIVACION_NATIVA_165R3276
@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def solicitudes_acceso_activar(request, solicitud_id):
    from django import forms
    from django.contrib import messages
    from django.contrib.auth import get_user_model
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404, redirect, render

    from accounts.models import SolicitudAcceso

    if not request.user.is_active or not request.user.is_superuser:
        raise PermissionDenied

    solicitud = get_object_or_404(
        SolicitudAcceso.objects.select_related("usuario_creado"),
        pk=solicitud_id,
    )

    if (
        solicitud.estado != SolicitudAcceso.Estado.APROBADA
        or not solicitud.usuario_creado_id
    ):
        return HttpResponse(
            "La solicitud no está aprobada o no tiene cuenta.",
            status=409,
        )

    if solicitud.usuario_creado.is_active:
        return HttpResponse(
            "La cuenta ya está activa.",
            status=409,
        )

    class FormularioActivacion(forms.Form):
        password = forms.CharField(
            label="Contraseña temporal",
            widget=forms.PasswordInput(
                attrs={"autocomplete": "new-password"}
            ),
        )
        confirmar = forms.CharField(
            label="Confirmar contraseña",
            widget=forms.PasswordInput(
                attrs={"autocomplete": "new-password"}
            ),
        )

        def clean(self):
            datos = super().clean()
            password = datos.get("password")
            confirmar = datos.get("confirmar")

            if password and confirmar and password != confirmar:
                self.add_error(
                    "confirmar",
                    "Las contraseñas no coinciden.",
                )

            return datos

    formulario = FormularioActivacion(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and formulario.is_valid():
        password = formulario.cleaned_data["password"]

        try:
            validate_password(
                password,
                user=solicitud.usuario_creado,
            )
        except ValidationError as error:
            formulario.add_error("password", error)
        else:
            with transaction.atomic():
                actual = get_object_or_404(
                    SolicitudAcceso.objects.select_for_update(),
                    pk=solicitud_id,
                )

                if (
                    actual.estado != SolicitudAcceso.Estado.APROBADA
                    or not actual.usuario_creado_id
                ):
                    return HttpResponse(
                        "La solicitud ya no está disponible.",
                        status=409,
                    )

                User = get_user_model()

                usuario = get_object_or_404(
                    User.objects.select_for_update(),
                    pk=actual.usuario_creado_id,
                )

                if usuario.is_active:
                    return HttpResponse(
                        "La cuenta ya está activa.",
                        status=409,
                    )

                usuario.set_password(password)
                usuario.is_active = True
                usuario.save(
                    update_fields=["password", "is_active"]
                )

                actual.cambio_password_obligatorio = True
                actual.save(
                    update_fields=["cambio_password_obligatorio"]
                )

            messages.success(
                request,
                "Cuenta activada correctamente. "
                "El usuario deberá cambiar su contraseña "
                "en el primer ingreso.",
            )

            return redirect(
                "solicitudes_acceso_revisar",
                solicitud_id,
            )

    return render(
        request,
        "accounts/solicitudes_acceso_activar.html",
        {
            "solicitud": solicitud,
            "formulario": formulario,
        },
    )


# PETCARE 165R.352.74 - DISPONIBILIDAD TUTOR
@login_required(login_url="petcare_login")
def disponibilidad_tutor(request):
    from datetime import date
    from django.http import JsonResponse
    from citas.disponibilidad import obtener_horas_disponibles
    from veterinarios.models import Veterinario

    usuario = request.user

    if (
        usuario.is_superuser
        or usuario.is_staff
        or usuario.groups.exists()
        or usuario.user_permissions.exists()
    ):
        return JsonResponse(
            {"error": "Acceso exclusivo para tutores."},
            status=403,
        )

    tutor = Tutor.objects.filter(
        usuario=usuario,
        activo=True,
    ).first()

    if tutor is None:
        return JsonResponse(
            {"error": "Tutor no autorizado."},
            status=403,
        )

    if request.method != "GET":
        return JsonResponse(
            {"error": "Metodo no permitido."},
            status=405,
        )

    try:
        veterinario_id = int(
            request.GET.get("veterinario", "")
        )
        fecha = date.fromisoformat(
            request.GET.get("fecha", "")
        )
    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Parametros invalidos."},
            status=400,
        )

    if not Veterinario.objects.filter(
        pk=veterinario_id,
        activo=True,
    ).exists():
        return JsonResponse(
            {"error": "Veterinario no disponible."},
            status=404,
        )

    horas = obtener_horas_disponibles(
        veterinario_id,
        fecha,
        duracion_minutos=30,
    )

    return JsonResponse({
        "fecha": fecha.isoformat(),
        "horas": horas,
        "total": len(horas),
    })
