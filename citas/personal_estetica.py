# PETCARE 165R.357.9.223 - PERSONAL ESTETICA

from django import forms
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .models import PersonalServicio


class PersonalEsteticaForm(forms.ModelForm):
    class Meta:
        model = PersonalServicio
        fields = [
            "rut",
            "nombre",
            "apellido",
            "especialidad",
            "telefono",
            "correo",
            "activo",
        ]
        widgets = {
            "rut": forms.TextInput(
                attrs={"placeholder": "12.345.678-5"}
            ),
            "nombre": forms.TextInput(
                attrs={"placeholder": "Nombre"}
            ),
            "apellido": forms.TextInput(
                attrs={"placeholder": "Apellido"}
            ),
            "especialidad": forms.TextInput(
                attrs={"placeholder": "Especialidad"}
            ),
            "telefono": forms.TextInput(
                attrs={"placeholder": "Teléfono"}
            ),
            "correo": forms.EmailInput(
                attrs={"placeholder": "Correo electrónico"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rut"].required = True

    def clean_rut(self):
        from tutores.models import validar_rut_chileno

        valor = (self.cleaned_data.get("rut") or "").strip()
        rut = valor.upper().replace(".", "").replace("-", "")

        validar_rut_chileno(rut)

        duplicado = PersonalServicio.objects.filter(
            rut=rut
        )

        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)

        if duplicado.exists():
            raise forms.ValidationError(
                "Este RUT ya está registrado."
            )

        return rut


@login_required(login_url="petcare_login")
@permission_required(
    "citas.view_personalservicio",
    raise_exception=True,
)
def lista_personal(request):
    # PETCARE 165R.357.9.224 - LISTADO MEJORADO
    from django.db.models import Q

    busqueda = request.GET.get("q", "").strip()[:100]

    base = PersonalServicio.objects.all()

    total = base.count()
    activos = base.filter(activo=True).count()
    inactivos = total - activos

    personal = base

    if busqueda:
        personal = personal.filter(
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
            | Q(especialidad__icontains=busqueda)
        )

    personal = personal.order_by("apellido", "nombre")

    return render(
        request,
        "citas/personal_estetica_lista.html",
        {
            "personal": personal,
            "total": total,
            "activos": activos,
            "inactivos": inactivos,
            "busqueda": busqueda,
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.add_personalservicio",
    raise_exception=True,
)
def crear_personal(request):
    formulario = PersonalEsteticaForm(
        request.POST or None
    )

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Personal de estética registrado correctamente.",
        )
        return redirect("citas:personal_estetica")

    return render(
        request,
        "citas/personal_estetica_form.html",
        {
            "formulario": formulario,
            "titulo": "Registrar personal de estética",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_personalservicio",
    raise_exception=True,
)
def editar_personal(request, pk):
    persona = get_object_or_404(
        PersonalServicio,
        pk=pk,
    )

    formulario = PersonalEsteticaForm(
        request.POST or None,
        instance=persona,
    )

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Personal actualizado correctamente.",
        )
        return redirect("citas:personal_estetica")

    return render(
        request,
        "citas/personal_estetica_form.html",
        {
            "formulario": formulario,
            "titulo": "Editar personal de estética",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_personalservicio",
    raise_exception=True,
)
@require_POST
def cambiar_activo_personal(request, pk):
    with transaction.atomic():
        persona = get_object_or_404(
            PersonalServicio.objects.select_for_update(),
            pk=pk,
        )
        persona.activo = not persona.activo
        persona.save(update_fields=["activo"])

    messages.success(
        request,
        "Estado del personal actualizado.",
    )
    return redirect("citas:personal_estetica")
