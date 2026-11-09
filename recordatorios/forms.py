from django import forms
from django.utils import timezone
from .models import Vacuna, ControlVeterinario


class VacunaForm(forms.ModelForm):
    class Meta:
        model = Vacuna
        fields = [
            "ficha",
            "veterinario",
            "nombre",
            "fecha_aplicacion",
            "proxima_dosis",
            "lote",
            "observaciones",
        ]
        widgets = {
            "fecha_aplicacion": forms.DateInput(attrs={"type": "date"}),
            "proxima_dosis": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


    # PETCARE VALIDACIONES 165R.333.1
    def clean(self):
        datos = super().clean()
        aplicacion = datos.get("fecha_aplicacion")
        proxima = datos.get("proxima_dosis")

        if aplicacion and proxima and proxima < aplicacion:
            self.add_error(
                "proxima_dosis",
                "La próxima dosis no puede ser anterior a la fecha de aplicación."
            )

        return datos


class ControlVeterinarioForm(forms.ModelForm):
    class Meta:
        model = ControlVeterinario
        fields = [
            "ficha",
            "veterinario",
            "motivo",
            "fecha_programada",
            "estado",
            "observaciones",
        ]
        widgets = {
            "fecha_programada": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


    # PETCARE VALIDACIONES 165R.333.1
    def clean(self):
        datos = super().clean()
        fecha = datos.get("fecha_programada")
        estado = datos.get("estado")

        if (
            self.instance._state.adding
            and fecha
            and estado == ControlVeterinario.Estado.PENDIENTE
            and fecha < timezone.localdate()
        ):
            self.add_error(
                "fecha_programada",
                "Un control pendiente nuevo no puede programarse en una fecha pasada."
            )

        return datos


# PETCARE FORMULARIOS 165R.331.1
def personalizar_campos_petcare(formulario):
    # PETCARE SELECTOR MASCOTAS 165R.332.2
    if "ficha" in formulario.fields:
        formulario.fields["ficha"].label_from_instance = (
            lambda ficha: (
                f"{ficha.mascota.nombre} · "
                f"Ficha clínica N.º {ficha.pk}"
            )
        )

    if "ficha" in formulario.fields:
        formulario.fields["ficha"].label = "Ficha clínica / Mascota"
        formulario.fields["ficha"].empty_label = "Seleccione una mascota"

    if "veterinario" in formulario.fields:
        formulario.fields["veterinario"].label = "Veterinario responsable"
        formulario.fields["veterinario"].empty_label = "Seleccione un veterinario"

    if "nombre" in formulario.fields:
        formulario.fields["nombre"].label = "Nombre de la vacuna"

    if "fecha_aplicacion" in formulario.fields:
        formulario.fields["fecha_aplicacion"].label = "Fecha de aplicación"

    if "proxima_dosis" in formulario.fields:
        formulario.fields["proxima_dosis"].label = "Próxima dosis"

    if "fecha_programada" in formulario.fields:
        formulario.fields["fecha_programada"].label = "Fecha programada"

    return formulario
