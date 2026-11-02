from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Cita
from .forms import CitaForm



def citas_visibles_para_usuario(usuario, queryset=None):
    """
    Limita las citas al ambito autorizado del usuario.
    """
    if queryset is None:
        queryset = Cita.objects.all()

    if not usuario.is_authenticated:
        return queryset.none()

    if usuario.is_superuser:
        return queryset

    grupos = set(
        usuario.groups.values_list("name", flat=True)
    )

    if grupos.intersection(
        {"Administrador", "Recepcionista"}
    ):
        return queryset

    if "Veterinario" in grupos:
        return queryset.filter(
            veterinario__usuario=usuario,
            veterinario__activo=True,
        )

    return queryset.none()


@login_required(login_url="/admin/login/")
@permission_required("citas.view_cita", raise_exception=True)
def lista_citas(request):
    busqueda = request.GET.get("q", "").strip()
    filtro = request.GET.get("filtro", "activas").strip().lower()

    filtros_validos = (
        "activas",
        "completadas",
        "canceladas",
        "archivadas",
    )

    if filtro not in filtros_validos:
        filtro = "activas"

    citas = Cita.objects.select_related(
        "mascota",
        "mascota__tutor",
        "veterinario",
    )

    # Control de acceso por rol y vinculacion profesional.
    # Administracion y recepcion consultan todas las citas.
    # Veterinarios consultan exclusivamente las propias.
    citas = citas_visibles_para_usuario(request.user, citas)

    if filtro == "activas":
        citas = citas.filter(
            archivada=False,
            estado__in=[
                Cita.Estado.PROGRAMADA,
                Cita.Estado.CONFIRMADA,
            ],
        )
    elif filtro == "completadas":
        citas = citas.filter(
            archivada=False,
            estado=Cita.Estado.COMPLETADA,
        )
    elif filtro == "canceladas":
        citas = citas.filter(
            archivada=False,
            estado=Cita.Estado.CANCELADA,
        )
    else:
        citas = citas.filter(archivada=True)

    if busqueda:
        citas = citas.filter(
            Q(mascota__nombre__icontains=busqueda)
            | Q(mascota__tutor__nombre__icontains=busqueda)
            | Q(mascota__tutor__apellido__icontains=busqueda)
            | Q(veterinario__nombre__icontains=busqueda)
            | Q(veterinario__apellido__icontains=busqueda)
        )

    citas = citas.order_by("fecha", "hora_inicio")

    return render(
        request,
        "citas/lista.html",
        {
            "citas": citas,
            "busqueda": busqueda,
            "filtro": filtro,
            "total_citas": citas.count(),
        },
    )


@login_required(login_url="/admin/login/")
@permission_required("citas.add_cita", raise_exception=True)
def crear_cita(request):
    if request.method == "POST":
        formulario = CitaForm(request.POST)

        if formulario.is_valid():
            formulario.save()
            return redirect("citas:lista")
    else:
        formulario = CitaForm()

    return render(
        request,
        "citas/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nueva cita",
            "modo_edicion": False,
        },
    )


@login_required(login_url="/admin/login/")
@permission_required("citas.change_cita", raise_exception=True)
def editar_cita(request, pk):
    cita = get_object_or_404(citas_visibles_para_usuario(request.user), pk=pk)

    # Proteger las citas completadas o archivadas.
    if cita.archivada or cita.estado == Cita.Estado.COMPLETADA:
        messages.error(
            request,
            "No se puede editar una cita completada o archivada.",
        )
        return redirect("citas:lista")

    if request.method == "POST":
        formulario = CitaForm(request.POST, instance=cita)

        if formulario.is_valid():
            formulario.save()
            return redirect("citas:lista")
    else:
        formulario = CitaForm(instance=cita)

    return render(
        request,
        "citas/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar cita",
            "modo_edicion": True,
            "cita": cita,
        },
    )


# PETCARE - CAMBIO DE ESTADOS DE CITAS V1

@login_required(login_url="/admin/login/")
@permission_required("citas.change_cita", raise_exception=True)
@require_POST
def cambiar_estado_cita(request, pk):
    transiciones = {
        Cita.Estado.PROGRAMADA: {
            "confirmar": Cita.Estado.CONFIRMADA,
            "cancelar": Cita.Estado.CANCELADA,
        },
        Cita.Estado.CONFIRMADA: {
            "completar": Cita.Estado.COMPLETADA,
            "cancelar": Cita.Estado.CANCELADA,
        },
    }

    accion = request.POST.get("accion", "").strip().lower()

    with transaction.atomic():
        cita = get_object_or_404(
            citas_visibles_para_usuario(request.user, Cita.objects.select_for_update()),
            pk=pk,
        )

        nuevo_estado = transiciones.get(
            cita.estado, {}
        ).get(accion)

        if nuevo_estado is None:
            messages.error(
                request,
                "No se permite este cambio de estado.",
            )
            return redirect("citas:lista")

        # Impedir completar una cita antes de su hora de termino.
        if nuevo_estado == Cita.Estado.COMPLETADA:
            from datetime import datetime, timedelta
            from django.utils import timezone

            inicio = datetime.combine(
                cita.fecha,
                cita.hora_inicio,
            )
            fin = inicio + timedelta(
                minutes=cita.duracion_minutos
            )

            ahora = timezone.localtime()
            fin = timezone.make_aware(
                fin,
                timezone.get_current_timezone(),
            )

            if ahora < fin:
                messages.error(
                    request,
                    "No se puede completar una cita antes "
                    "de su hora de termino.",
                )
                return redirect("citas:lista")

        cita.estado = nuevo_estado
        cita.save(update_fields=["estado"])

    messages.success(
        request,
        "Estado de la cita actualizado correctamente.",
    )

    return redirect("citas:lista")


# PETCARE - ARCHIVAR CITAS V1

@login_required(login_url="/admin/login/")
@permission_required("citas.change_cita", raise_exception=True)
@require_POST
def archivar_cita(request, pk):
    with transaction.atomic():
        cita = get_object_or_404(
            citas_visibles_para_usuario(request.user, Cita.objects.select_for_update()),
            pk=pk,
        )

        if cita.archivada:
            messages.info(
                request,
                "Esta cita ya se encuentra archivada.",
            )
        elif cita.estado not in (
            Cita.Estado.COMPLETADA,
            Cita.Estado.CANCELADA,
        ):
            messages.error(
                request,
                "Solo se pueden archivar citas completadas o canceladas.",
            )
        else:
            cita.archivada = True
            cita.save(update_fields=["archivada"])

            messages.success(
                request,
                "Cita archivada correctamente.",
            )

    return redirect("citas:lista")


# PETCARE RESTAURAR CITAS V1

@login_required(login_url="/admin/login/")
@permission_required("citas.change_cita", raise_exception=True)
@require_POST
def restaurar_cita(request, pk):
    with transaction.atomic():
        cita = get_object_or_404(
            citas_visibles_para_usuario(request.user, Cita.objects.select_for_update()),
            pk=pk,
        )

        if not cita.archivada:
            messages.info(
                request,
                "Esta cita no se encuentra archivada.",
            )
        elif cita.estado not in (
            Cita.Estado.COMPLETADA,
            Cita.Estado.CANCELADA,
        ):
            messages.error(
                request,
                "No se puede restaurar una cita con este estado.",
            )
        else:
            cita.archivada = False
            cita.save(update_fields=["archivada"])

            messages.success(
                request,
                "Cita restaurada correctamente.",
            )

    return redirect("citas:lista")
