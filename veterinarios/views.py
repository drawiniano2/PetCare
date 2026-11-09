from django.shortcuts import redirect, get_object_or_404
from .forms import VeterinarioForm
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import render

from .models import Veterinario


@login_required(login_url="petcare_login")
@permission_required("veterinarios.view_veterinario", raise_exception=True)
def lista_veterinarios(request):
    busqueda = request.GET.get("q", "").strip()

    veterinarios = Veterinario.objects.all()

    if busqueda:
        veterinarios = veterinarios.filter(
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
            | Q(rut__icontains=busqueda)
            | Q(especialidad__icontains=busqueda)
            | Q(numero_registro__icontains=busqueda)
            | Q(correo__icontains=busqueda)
        )

    return render(
        request,
        "veterinarios/lista.html",
        {
            "veterinarios": veterinarios,
            "busqueda": busqueda,
            "total_veterinarios": veterinarios.count(),
        },
    )


@login_required(login_url="petcare_login")
@permission_required("veterinarios.add_veterinario", raise_exception=True)
def crear_veterinario(request):
    if request.method == "POST":
        formulario = VeterinarioForm(request.POST)

        if formulario.is_valid():
            formulario.save()
            return redirect("veterinarios:lista")
    else:
        formulario = VeterinarioForm()

    return render(
        request,
        "veterinarios/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo veterinario",
        },
    )



@login_required(login_url="petcare_login")
@permission_required("veterinarios.view_veterinario", raise_exception=True)
def detalle_veterinario(request, pk):
    veterinario = get_object_or_404(Veterinario, pk=pk)

    return render(
        request,
        "veterinarios/detalle.html",
        {"veterinario": veterinario},
    )


@login_required(login_url="petcare_login")
@permission_required("veterinarios.change_veterinario", raise_exception=True)
def editar_veterinario(request, pk):
    veterinario = get_object_or_404(Veterinario, pk=pk)

    if request.method == "POST":
        formulario = VeterinarioForm(request.POST, instance=veterinario)

        if formulario.is_valid():
            formulario.save()
            return redirect("veterinarios:detalle", pk=veterinario.pk)
    else:
        formulario = VeterinarioForm(instance=veterinario)

    return render(
        request,
        "veterinarios/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar veterinario",
            "veterinario": veterinario,
        },
    )
