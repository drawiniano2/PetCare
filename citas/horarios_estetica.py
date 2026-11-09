# PETCARE 165R.357.9.227 - HORARIOS ESTETICA

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .models import (
    HorarioPersonalServicio,
    PersonalServicio,
)


class HorarioEsteticaForm(forms.ModelForm):
    class Meta:
        model = HorarioPersonalServicio
        fields = [
            "personal",
            "dia_semana",
            "hora_inicio",
            "hora_fin",
            "activo",
        ]
        widgets = {
            "hora_inicio": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time"},
            ),
            "hora_fin": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        personal = PersonalServicio.objects.filter(
            activo=True
        )

        if self.instance.pk:
            personal = PersonalServicio.objects.filter(
                activo=True
            ) | PersonalServicio.objects.filter(
                pk=self.instance.personal_id
            )

        self.fields["personal"].queryset = (
            personal.distinct().order_by("apellido", "nombre")
        )
        self.fields["personal"].empty_label = (
            "Seleccione personal de estética"
        )
        # PETCARE 165R.357.9.230 - DIA EN ESPAÑOL
        self.fields["dia_semana"].choices = [
            ("", "Seleccione un día"),
            *[
                (valor, etiqueta)
                for valor, etiqueta in
                HorarioPersonalServicio.DiaSemana.choices
            ],
        ]

    def clean(self):
        datos = super().clean()

        personal = datos.get("personal")
        dia = datos.get("dia_semana")
        inicio = datos.get("hora_inicio")
        fin = datos.get("hora_fin")
        activo = datos.get("activo")

        if inicio and fin and inicio >= fin:
            self.add_error(
                "hora_fin",
                "La hora de término debe ser posterior al inicio.",
            )

        if personal and activo and not personal.activo:
            self.add_error(
                "personal",
                "No se pueden activar horarios de personal inactivo.",
            )

        if (
            personal is not None
            and dia is not None
            and inicio is not None
            and fin is not None
            and inicio < fin
            and activo
        ):
            existentes = HorarioPersonalServicio.objects.filter(
                personal=personal,
                dia_semana=dia,
                activo=True,
                hora_inicio__lt=fin,
                hora_fin__gt=inicio,
            )

            if self.instance.pk:
                existentes = existentes.exclude(
                    pk=self.instance.pk
                )

            if existentes.exists():
                self.add_error(
                    "hora_inicio",
                    "Este horario se superpone con otro horario activo.",
                )

        return datos


@login_required(login_url="petcare_login")
@permission_required(
    "citas.view_horariopersonalservicio",
    raise_exception=True,
)
def lista_horarios(request):
    horarios = (
        HorarioPersonalServicio.objects
        .select_related("personal")
        .order_by("personal__apellido", "dia_semana", "hora_inicio")
    )

    return render(
        request,
        "citas/horarios_estetica_lista.html",
        {"horarios": horarios},
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.add_horariopersonalservicio",
    raise_exception=True,
)
def crear_horario(request):
    formulario = HorarioEsteticaForm(
        request.POST or None
    )

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Horario de estética registrado correctamente.",
        )
        return redirect("citas:horarios_estetica")

    return render(
        request,
        "citas/horarios_estetica_form.html",
        {
            "formulario": formulario,
            "titulo": "Registrar horario de estética",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_horariopersonalservicio",
    raise_exception=True,
)
def editar_horario(request, pk):
    horario = get_object_or_404(
        HorarioPersonalServicio,
        pk=pk,
    )

    formulario = HorarioEsteticaForm(
        request.POST or None,
        instance=horario,
    )

    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Horario de estética actualizado.",
        )
        return redirect("citas:horarios_estetica")

    return render(
        request,
        "citas/horarios_estetica_form.html",
        {
            "formulario": formulario,
            "titulo": "Editar horario de estética",
        },
    )


@login_required(login_url="petcare_login")
@permission_required(
    "citas.change_horariopersonalservicio",
    raise_exception=True,
)
@require_POST
def cambiar_estado_horario(request, pk):
    with transaction.atomic():
        horario = get_object_or_404(
            HorarioPersonalServicio.objects.select_for_update(),
            pk=pk,
        )

        if not horario.activo:
            formulario = HorarioEsteticaForm(
                instance=horario,
                data={
                    "personal": horario.personal_id,
                    "dia_semana": horario.dia_semana,
                    "hora_inicio": horario.hora_inicio.strftime("%H:%M"),
                    "hora_fin": horario.hora_fin.strftime("%H:%M"),
                    "activo": "on",
                },
            )

            if not formulario.is_valid():
                messages.error(
                    request,
                    "No se puede activar: horario superpuesto "
                    "o personal inactivo.",
                )
                return redirect("citas:horarios_estetica")

        horario.activo = not horario.activo
        horario.save(update_fields=["activo"])

    messages.success(
        request,
        "Estado del horario actualizado.",
    )
    return redirect("citas:horarios_estetica")
