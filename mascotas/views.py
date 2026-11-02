from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MascotaForm
from .models import Mascota


@login_required(login_url="/admin/login/")
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


@login_required(login_url="/admin/login/")
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


@login_required(login_url="/admin/login/")
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


@login_required(login_url="/admin/login/")
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
