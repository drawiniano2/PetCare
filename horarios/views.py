from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.db.models import Q
from django.shortcuts import render

from .models import Horario


@login_required(login_url="/admin/login/")
@permission_required("horarios.view_horario", raise_exception=True)
def lista_horarios(request):
    busqueda = request.GET.get("q", "").strip()

    horarios = Horario.objects.select_related(
        "veterinario"
    ).order_by(
        "dia_semana",
        "hora_inicio",
        "veterinario__apellido",
    )

    if busqueda:
        horarios = horarios.filter(
            Q(veterinario__nombre__icontains=busqueda)
            | Q(veterinario__apellido__icontains=busqueda)
            | Q(veterinario__especialidad__icontains=busqueda)
            | Q(veterinario__rut__icontains=busqueda)
        )

    return render(
        request,
        "horarios/lista.html",
        {
            "horarios": horarios,
            "total_horarios": horarios.count(),
            "busqueda": busqueda,
        },
    )


from django.shortcuts import get_object_or_404, redirect
from .forms import HorarioForm


@login_required(login_url="/admin/login/")
@permission_required("horarios.add_horario", raise_exception=True)
def crear_horario(request):

    if request.method == "POST":
        formulario = HorarioForm(request.POST)

        if formulario.is_valid():
            formulario.save()
            return redirect("horarios:lista")

    else:
        formulario = HorarioForm()

    return render(
        request,
        "horarios/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo horario",
            "modo_edicion": False,
        },
    )


@login_required(login_url="/admin/login/")
@permission_required("horarios.change_horario", raise_exception=True)
def editar_horario(request, pk):

    horario = get_object_or_404(Horario, pk=pk)

    if request.method == "POST":
        formulario = HorarioForm(
            request.POST,
            instance=horario,
        )

        if formulario.is_valid():
            formulario.save()
            return redirect("horarios:lista")

    else:
        formulario = HorarioForm(instance=horario)

    return render(
        request,
        "horarios/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar horario",
            "modo_edicion": True,
            "horario": horario,
        },
    )


from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import ValidationError


@login_required(login_url="/admin/login/")
@permission_required("horarios.change_horario", raise_exception=True)
@require_POST
def cambiar_estado_horario(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    horario.activo = not horario.activo

    try:
        horario.save(update_fields=["activo"])
    except ValidationError as error:
        messages.error(
            request,
            "No fue posible cambiar el estado: "
            + "; ".join(error.messages)
        )
    else:
        messages.success(
            request,
            "Horario activado correctamente."
            if horario.activo
            else "Horario desactivado correctamente."
        )

    return redirect("horarios:lista")
