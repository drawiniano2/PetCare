from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .models import Tutor
from .forms import TutorForm


@login_required(login_url="petcare_login")
@permission_required("tutores.view_tutor", raise_exception=True)
def lista_tutores(request):
    busqueda = request.GET.get("q", "").strip()

    tutores = Tutor.objects.all()

    if busqueda:
        tutores = tutores.filter(
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
            | Q(rut__icontains=busqueda)
            | Q(correo__icontains=busqueda)
        )

    contexto = {
        "tutores": tutores,
        "busqueda": busqueda,
        "total_tutores": Tutor.objects.count(),
    }

    return render(request, "tutores/lista.html", contexto)


@login_required(login_url="petcare_login")
@permission_required("tutores.add_tutor", raise_exception=True)
def crear_tutor(request):
    if request.method == "POST":
        formulario = TutorForm(request.POST)

        if formulario.is_valid():
            formulario.save()
            return redirect("tutores:lista")
    else:
        formulario = TutorForm()

    return render(request, "tutores/formulario.html", {
        "formulario": formulario,
        "titulo": "Nuevo tutor",
        "texto_boton": "Guardar tutor",
    })


@login_required(login_url="petcare_login")
@permission_required("tutores.change_tutor", raise_exception=True)
def editar_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    if request.method == "POST":
        formulario = TutorForm(request.POST, instance=tutor)

        if formulario.is_valid():
            formulario.save()
            return redirect("tutores:lista")
    else:
        formulario = TutorForm(instance=tutor)

    return render(request, "tutores/formulario.html", {
        "formulario": formulario,
        "titulo": "Editar tutor",
        "texto_boton": "Guardar cambios",
    })


@login_required(login_url="petcare_login")
@permission_required("tutores.view_tutor", raise_exception=True)
def detalle_tutor(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    return render(request, "tutores/detalle.html", {
        "tutor": tutor,
        "mascotas": tutor.mascotas.all(),
    })


