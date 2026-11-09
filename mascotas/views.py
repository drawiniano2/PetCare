from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MascotaForm
from .models import Mascota


@login_required(login_url="petcare_login")
@permission_required("mascotas.view_mascota", raise_exception=True)
def lista_mascotas(request):
    busqueda = request.GET.get("q", "").strip()

    mascotas = Mascota.objects.select_related("tutor").all()

    if busqueda:
        mascotas = mascotas.filter(
            Q(nombre__icontains=busqueda)
            | Q(raza__icontains=busqueda)
            | Q(especie__icontains=busqueda)
            | Q(tutor__nombre__icontains=busqueda)
            | Q(tutor__apellido__icontains=busqueda)
            | Q(tutor__rut__icontains=busqueda)
            | Q(microchip__icontains=busqueda)
        )

    contexto = {
        "mascotas": mascotas,
        "busqueda": busqueda,
        "total_mascotas": mascotas.count(),
    }

    return render(request, "mascotas/lista.html", contexto)


@login_required(login_url="petcare_login")
@permission_required("mascotas.view_mascota", raise_exception=True)
def detalle_mascota(request, pk):
    mascota = get_object_or_404(
        Mascota.objects.select_related("tutor"),
        pk=pk,
    )

    return render(
        request,
        "mascotas/detalle.html",
        {"mascota": mascota},
    )


@login_required(login_url="petcare_login")
@permission_required("mascotas.add_mascota", raise_exception=True)
def crear_mascota(request):
    if request.method == "POST":
        formulario = MascotaForm(request.POST)

        if formulario.is_valid():
            mascota = formulario.save()
            return redirect("mascotas:detalle", pk=mascota.pk)
    else:
        formulario = MascotaForm()

    return render(
        request,
        "mascotas/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Registrar nueva mascota",
            "subtitulo": "Ingrese los datos del paciente veterinario.",
            "texto_boton": "Guardar mascota",
            "es_edicion": False,
        },
    )


@login_required(login_url="petcare_login")
@permission_required("mascotas.change_mascota", raise_exception=True)
def editar_mascota(request, pk):
    mascota = get_object_or_404(Mascota, pk=pk)

    if request.method == "POST":
        formulario = MascotaForm(request.POST, instance=mascota)

        if formulario.is_valid():
            mascota = formulario.save()
            return redirect("mascotas:detalle", pk=mascota.pk)
    else:
        formulario = MascotaForm(instance=mascota)

    return render(
        request,
        "mascotas/formulario.html",
        {
            "formulario": formulario,
            "mascota": mascota,
            "titulo": "Editar mascota",
            "subtitulo": "Actualice los datos del paciente veterinario.",
            "texto_boton": "Guardar cambios",
            "es_edicion": True,
        },
    )


# PETCARE_SOLICITUDES_PANEL
@login_required(login_url="petcare_login")
@permission_required("mascotas.view_solicitudmascota", raise_exception=True)
def lista_solicitudes_mascotas(request):
    from django.core.exceptions import PermissionDenied
    from django.core.paginator import Paginator
    from .models import SolicitudMascota

    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    estado = request.GET.get("estado", "").strip().upper()
    busqueda = request.GET.get("q", "").strip()

    solicitudes = SolicitudMascota.objects.select_related("tutor")

    estados_validos = {
        SolicitudMascota.Estado.PENDIENTE,
        SolicitudMascota.Estado.APROBADA,
        SolicitudMascota.Estado.RECHAZADA,
    }

    if estado in estados_validos:
        solicitudes = solicitudes.filter(estado=estado)
    else:
        estado = ""

    if busqueda:
        solicitudes = solicitudes.filter(
            Q(nombre__icontains=busqueda)
            | Q(tutor__nombre__icontains=busqueda)
            | Q(tutor__apellido__icontains=busqueda)
            | Q(tutor__rut__icontains=busqueda)
            | Q(microchip__icontains=busqueda)
        )

    pagina = Paginator(solicitudes, 10).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "mascotas/solicitudes_lista.html",
        {
            "solicitudes": pagina,
            "estado": estado,
            "busqueda": busqueda,
            "total": solicitudes.count(),
        },
    )


# PETCARE_REVISION_SOLICITUDES_PANEL
@login_required(login_url="petcare_login")
@permission_required("mascotas.view_solicitudmascota", raise_exception=True)
def revisar_solicitud_mascota(request, solicitud_id):
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied, ValidationError
    from django.db import IntegrityError
    from .models import SolicitudMascota
    from .servicios_solicitudes import (
        aprobar_mascota_nueva,
        aprobar_vinculacion_mascota,
        rechazar_solicitud,
    )

    usuario = request.user

    if not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied

    solicitud = get_object_or_404(
        SolicitudMascota.objects.select_related(
            "tutor", "revisado_por"
        ),
        pk=solicitud_id,
    )

    puede_decidir = usuario.has_perm(
        "mascotas.change_solicitudmascota"
    )

    error = None
    motivo = ""

    # PETCARE_CONSULTA_MASCOTA_VINCULACION
    from .models import Mascota

    # PETCARE_TOKEN_TRANSFERENCIA
    from django.core import signing

    mascota_existente = None
    token_transferencia = ""
    mascota_id_consulta = request.GET.get(
        "mascota_id", ""
    ).strip()

    if solicitud.tipo == SolicitudMascota.Tipo.VINCULAR:
        if mascota_id_consulta:
            if mascota_id_consulta.isdigit():
                mascota_existente = (
                    Mascota.objects.select_related("tutor")
                    .filter(pk=int(mascota_id_consulta))
                    .first()
                )
                if mascota_existente is None:
                    error = "No se encontró la mascota indicada."
                else:
                    token_transferencia = signing.dumps(
                        {
                            "solicitud": solicitud.pk,
                            "mascota": mascota_existente.pk,
                            "tutor_actual": mascota_existente.tutor_id,
                            "usuario": usuario.pk,
                        },
                        salt="petcare-transferencia-mascota",
                    )
            else:
                error = "Ingrese un ID de mascota válido."

    if request.method == "POST":
        if not puede_decidir:
            raise PermissionDenied

        accion = request.POST.get("accion", "")
        confirmado = request.POST.get("confirmar") == "si"
        motivo = request.POST.get("motivo", "").strip()

        if solicitud.estado != SolicitudMascota.Estado.PENDIENTE:
            error = "La solicitud ya fue revisada."

        elif not confirmado:
            error = "Debe confirmar la decisión."

        elif accion not in ("aprobar", "rechazar"):
            error = "Acción no válida."

        else:
            try:
                if accion == "aprobar":
                    if solicitud.tipo == SolicitudMascota.Tipo.VINCULAR:
                        try:
                            datos = signing.loads(
                                request.POST.get("token_transferencia", ""),
                                salt="petcare-transferencia-mascota",
                                max_age=900,
                            )
                        except signing.BadSignature:
                            raise ValidationError(
                                "Debe consultar nuevamente la mascota."
                            )

                        if (
                            datos.get("solicitud") != solicitud.pk
                            or datos.get("usuario") != usuario.pk
                            or str(datos.get("mascota")) !=
                            request.POST.get("mascota_id", "").strip()
                            or str(datos.get("tutor_actual")) !=
                            request.POST.get("tutor_actual_id", "").strip()
                        ):
                            raise ValidationError(
                                "Los antecedentes confirmados no coinciden."
                            )

                        aprobar_vinculacion_mascota(
                            solicitud.pk,
                            usuario,
                            request.POST.get("mascota_id", "").strip(),
                            motivo,
                            titularidad_verificada=(
                                request.POST.get("titularidad_verificada") == "si"
                            ),
                            tutor_actual_id_confirmado=request.POST.get(
                                "tutor_actual_id", ""
                            ),
                        )
                    else:
                        aprobar_mascota_nueva(
                            solicitud.pk, usuario, motivo
                        )
                    messages.success(
                        request, "Solicitud aprobada correctamente."
                    )
                else:
                    rechazar_solicitud(
                        solicitud.pk, usuario, motivo
                    )
                    messages.success(
                        request, "Solicitud rechazada correctamente."
                    )

                return redirect("mascotas:solicitudes_lista")

            except ValidationError as exc:
                error = "; ".join(exc.messages)

            except IntegrityError:
                error = "Conflicto de integridad."

    return render(
        request,
        "mascotas/solicitudes_revisar.html",
        {
            "solicitud": solicitud,
            "puede_decidir": puede_decidir,
            "puede_aprobar": (
                puede_decidir
                and solicitud.estado == SolicitudMascota.Estado.PENDIENTE
            ),
            "puede_rechazar": (
                puede_decidir
                and solicitud.estado == SolicitudMascota.Estado.PENDIENTE
            ),
            "error_revision": error,
            "motivo": motivo,
            "mascota_existente": mascota_existente,
            "mascota_id_consulta": mascota_id_consulta,
            "token_transferencia": token_transferencia,
        },
    )
