from datetime import timedelta, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    VacunaForm,
    ControlVeterinarioForm,
    personalizar_campos_petcare,
)
from .models import Vacuna, ControlVeterinario
from .permisos import (
    exigir_gestion,
    fichas_visibles,
    perfil_usuario,
    veterinarios_asignables,
)


def registros_visibles(usuario, modelo):
    return modelo.objects.filter(ficha__in=fichas_visibles(usuario))


def exigir_permiso(usuario, modelo, accion):
    permiso = f"{modelo._meta.app_label}.{accion}_{modelo._meta.model_name}"
    if not usuario.has_perm(permiso):
        raise PermissionDenied


def puede_editar(usuario, registro):
    perfil = perfil_usuario(usuario)

    if perfil == "ADMINISTRADOR":
        return True

    return (
        perfil == "VETERINARIO"
        and registro.veterinario.usuario_id == usuario.pk
        and registro.veterinario.activo
        and fichas_visibles(usuario).filter(pk=registro.ficha_id).exists()
    )


def configurar_formulario(formulario, usuario):
    formulario.fields["ficha"].queryset = fichas_visibles(usuario)
    formulario.fields["veterinario"].queryset = veterinarios_asignables(usuario)
    return formulario


@login_required(login_url="petcare_login")
def lista(request):
    exigir_gestion(request.user)
    exigir_permiso(request.user, Vacuna, "view")
    exigir_permiso(request.user, ControlVeterinario, "view")

    hoy = timezone.localdate()
    limite = hoy + timedelta(days=30)

    vacunas = registros_visibles(
        request.user, Vacuna
    ).select_related("ficha__mascota", "veterinario")

    controles = registros_visibles(
        request.user, ControlVeterinario
    ).select_related("ficha__mascota", "veterinario")

    # PETCARE FILTROS 165R.330.2
    busqueda = request.GET.get("q", "").strip()[:100]
    estado = request.GET.get("estado", "").strip()
    fecha_desde = request.GET.get("desde", "").strip()
    fecha_hasta = request.GET.get("hasta", "").strip()

    # Los indicadores se calculan antes de filtrar.
    # Así conservan los totales sanitarios autorizados.

    indicadores = {
        "vacunas_proximas": vacunas.filter(
            proxima_dosis__gte=hoy,
            proxima_dosis__lte=limite,
        ).count(),
        "vacunas_vencidas": vacunas.filter(
            proxima_dosis__lt=hoy,
        ).count(),
        "controles_proximos": controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada__gte=hoy,
            fecha_programada__lte=limite,
        ).count(),
        "controles_vencidos": controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada__lt=hoy,
        ).count(),
    }

    # PETCARE FILTROS ACTIVOS 165R.330.3
    if busqueda:
        vacunas = vacunas.filter(
            Q(ficha__mascota__nombre__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
        )
        controles = controles.filter(
            Q(ficha__mascota__nombre__icontains=busqueda)
            | Q(motivo__icontains=busqueda)
        )

    estados_validos = {
        "vencido", "hoy", "proximo",
        "pendiente", "realizado", "cancelado",
    }

    if estado not in estados_validos:
        estado = ""

    if estado == "vencido":
        vacunas = vacunas.filter(proxima_dosis__lt=hoy)
        controles = controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada__lt=hoy,
        )

    elif estado == "hoy":
        vacunas = vacunas.filter(proxima_dosis=hoy)
        controles = controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada=hoy,
        )

    elif estado == "proximo":
        vacunas = vacunas.filter(
            proxima_dosis__gt=hoy,
            proxima_dosis__lte=limite,
        )
        controles = controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada__gt=hoy,
            fecha_programada__lte=limite,
        )

    elif estado == "pendiente":
        controles = controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE
        )
        vacunas = vacunas.none()

    elif estado == "realizado":
        controles = controles.filter(
            estado=ControlVeterinario.Estado.REALIZADO
        )
        vacunas = vacunas.none()

    elif estado == "cancelado":
        controles = controles.filter(
            estado=ControlVeterinario.Estado.CANCELADO
        )
        vacunas = vacunas.none()

    def convertir_fecha(valor):
        try:
            return date.fromisoformat(valor)
        except (ValueError, TypeError):
            return None

    desde = convertir_fecha(fecha_desde)
    hasta = convertir_fecha(fecha_hasta)

    if desde:
        vacunas = vacunas.filter(proxima_dosis__gte=desde)
        controles = controles.filter(
            fecha_programada__gte=desde
        )

    if hasta:
        vacunas = vacunas.filter(proxima_dosis__lte=hasta)
        controles = controles.filter(
            fecha_programada__lte=hasta
        )

    perfil = perfil_usuario(request.user)

    puede_crear_vacuna = request.user.has_perm(
        "recordatorios.add_vacuna"
    )
    puede_crear_control = request.user.has_perm(
        "recordatorios.add_controlveterinario"
    )

    puede_modificar_vacuna = request.user.has_perm(
        "recordatorios.change_vacuna"
    )
    puede_modificar_control = request.user.has_perm(
        "recordatorios.change_controlveterinario"
    )

    vacunas_editables = set()
    controles_editables = set()

    if puede_modificar_vacuna:
        vacunas_editables = {
            registro.pk
            for registro in vacunas
            if puede_editar(request.user, registro)
        }

    if puede_modificar_control:
        controles_editables = {
            registro.pk
            for registro in controles
            if puede_editar(request.user, registro)
        }

    for registro in vacunas:
        registro.mostrar_editar = registro.pk in vacunas_editables

    for registro in controles:
        registro.mostrar_editar = registro.pk in controles_editables

    return render(request, "recordatorios/lista.html", {
        "vacunas": vacunas,
        "controles": controles,
        "avisos_vacunas": vacunas.filter(
            proxima_dosis__isnull=False,
            proxima_dosis__lte=limite,
        ).order_by("proxima_dosis"),
        "avisos_controles": controles.filter(
            estado=ControlVeterinario.Estado.PENDIENTE,
            fecha_programada__lte=limite,
        ).order_by("fecha_programada"),
        "hoy": hoy,
        "filtro_busqueda": busqueda,
        "filtro_estado": estado,
        "filtro_desde": fecha_desde,
        "filtro_hasta": fecha_hasta,
        "indicadores": indicadores,
        "puede_crear_vacuna": puede_crear_vacuna,
        "puede_crear_control": puede_crear_control,
        "vacunas_editables": vacunas_editables,
        "controles_editables": controles_editables,
    })


def gestionar(request, modelo, formulario_clase, pk=None):
    exigir_gestion(request.user)
    exigir_permiso(
        request.user,
        modelo,
        "add" if pk is None else "change",
    )

    registro = None

    if pk is not None:
        registro = get_object_or_404(
            registros_visibles(request.user, modelo),
            pk=pk,
        )
        if not puede_editar(request.user, registro):
            raise PermissionDenied

    # PETCARE 165R.330.8 - ORIGEN FICHA CLINICA
    ficha_origen = None
    ficha_id = request.GET.get("ficha", "").strip()

    if ficha_id.isdecimal():
        ficha_origen = fichas_visibles(request.user).filter(
            pk=int(ficha_id)
        ).first()

    if registro is not None:
        if ficha_origen is None or ficha_origen.pk != registro.ficha_id:
            ficha_origen = None

    formulario = formulario_clase(
        request.POST if request.method == "POST" else None,
        instance=registro,
    )
    configurar_formulario(formulario, request.user)

    if (
        registro is None
        and request.method == "GET"
        and ficha_origen is not None
    ):
        formulario.fields["ficha"].initial = ficha_origen.pk

    # PETCARE FORMULARIOS ACTIVOS 165R.331.2
    personalizar_campos_petcare(formulario)

    if registro is not None and perfil_usuario(request.user) == "VETERINARIO":
        formulario.fields["ficha"].disabled = True
        formulario.fields["veterinario"].disabled = True

    if request.method == "POST" and formulario.is_valid():
        objeto = formulario.save(commit=False)
        objeto.save()

        # PETCARE CONFIRMACIONES 165R.333.2
        if modelo is Vacuna:
            mensaje = (
                "Vacuna registrada correctamente."
                if registro is None
                else "Vacuna actualizada correctamente."
            )
        else:
            mensaje = (
                "Control veterinario registrado correctamente."
                if registro is None
                else "Control veterinario actualizado correctamente."
            )

        messages.success(request, mensaje)

        if (
            ficha_origen is not None
            and objeto.ficha_id == ficha_origen.pk
        ):
            return redirect(
                "historial_clinico:detalle",
                mascota_id=ficha_origen.mascota_id,
            )

        return redirect("recordatorios_lista")

    return render(request, "recordatorios/formulario.html", {
        # PETCARE 165R.330.13 - CANCELAR A FICHA
        "ficha_origen": ficha_origen,
        "formulario": formulario,
        "registro": registro,
        "titulo": "Vacuna" if modelo is Vacuna else "Control veterinario",
    })


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def vacuna_crear(request):
    return gestionar(request, Vacuna, VacunaForm)


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def vacuna_editar(request, pk):
    return gestionar(request, Vacuna, VacunaForm, pk)


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def control_crear(request):
    return gestionar(request, ControlVeterinario, ControlVeterinarioForm)


@login_required(login_url="petcare_login")
@require_http_methods(["GET", "POST"])
def control_editar(request, pk):
    return gestionar(request, ControlVeterinario, ControlVeterinarioForm, pk)
