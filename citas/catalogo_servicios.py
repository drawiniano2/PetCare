# PETCARE 165R.357.9.234 - CATALOGO PROVISIONAL

from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.shortcuts import render

from .models import Servicio


# PETCARE 165R.357.9.237 - FILTROS CATALOGO
@login_required(login_url="petcare_login")
@permission_required(
    "citas.view_servicio",
    raise_exception=True,
)
def lista_servicios(request):
    from django.db.models import Q

    q = request.GET.get("q", "").strip()[:100]
    categoria = request.GET.get("categoria", "")
    estado = request.GET.get("estado", "")

    base = Servicio.objects.all()

    total = base.count()
    medicos = base.filter(categoria="MEDICO").count()
    estetica = base.filter(categoria="ESTETICA").count()

    servicios = base

    if q:
        servicios = servicios.filter(
            Q(nombre__icontains=q)
        )

    if categoria in ("MEDICO", "ESTETICA"):
        servicios = servicios.filter(
            categoria=categoria
        )

    if estado == "activo":
        servicios = servicios.filter(activo=True)
    elif estado == "inactivo":
        servicios = servicios.filter(activo=False)

    return render(
        request,
        "citas/catalogo_servicios_lista.html",
        {
            "servicios": servicios.order_by(
                "categoria", "nombre"
            ),
            "total": total,
            "medicos": medicos,
            "estetica": estetica,
            "q": q,
            "categoria": categoria,
            "estado": estado,
        },
    )


# PETCARE 165R.357.9.235 - ADMINISTRACION

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = [
            "nombre",
            "categoria",
            "duracion_minutos",
            "precio",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"placeholder": "Nombre del servicio"}
            ),
            "duracion_minutos": forms.NumberInput(
                attrs={"min": 1, "max": 480}
            ),
            "precio": forms.NumberInput(
                attrs={
                    "min": 0,
                    "step": 1,
                    "placeholder": "Ejemplo: 15000",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].choices = [
            ("", "Seleccione una categoría"),
            *Servicio.Categoria.choices,
        ]

    def clean_nombre(self):
        nombre = " ".join(
            self.cleaned_data["nombre"].split()
        )

        duplicados = Servicio.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance.pk:
            duplicados = duplicados.exclude(
                pk=self.instance.pk
            )

        if duplicados.exists():
            raise forms.ValidationError(
                "Ya existe un servicio con este nombre."
            )

        return nombre


@login_required(login_url="petcare_login")
@permission_required(
    "citas.add_servicio",
    raise_exception=True,
)
def crear_servicio(request):
    formulario = ServicioForm(request.POST or None)

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Servicio registrado correctamente.",
        )
        return redirect("citas:catalogo_servicios")

    return render(
        request,
        "citas/catalogo_servicios_form.html",
        {
            "formulario": formulario,
            "titulo": "Registrar servicio",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_servicio",
    raise_exception=True,
)
def editar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)

    formulario = ServicioForm(
        request.POST or None,
        instance=servicio,
    )

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Servicio actualizado correctamente.",
        )
        return redirect("citas:catalogo_servicios")

    return render(
        request,
        "citas/catalogo_servicios_form.html",
        {
            "formulario": formulario,
            "titulo": "Editar servicio",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_servicio",
    raise_exception=True,
)
@require_POST
def cambiar_estado_servicio(request, pk):
    with transaction.atomic():
        servicio = get_object_or_404(
            Servicio.objects.select_for_update(),
            pk=pk,
        )

        servicio.activo = not servicio.activo
        servicio.save(update_fields=["activo"])

    messages.success(
        request,
        "Estado del servicio actualizado.",
    )
    return redirect("citas:catalogo_servicios")

# PETCARE 165R.357.9.240 - PRECIO CLP
