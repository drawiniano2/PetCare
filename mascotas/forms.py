from django import forms

from tutores.models import Tutor
from .models import Mascota, SolicitudMascota


class MascotaForm(forms.ModelForm):

    class Meta:
        model = Mascota

        fields = [
            "tutor",
            "nombre",
            "especie",
            "raza",
            "sexo",
            "fecha_nacimiento",
            "color",
            "microchip",
            "peso",
            "observaciones",
            "activo",
        ]

        widgets = {
            "nombre": forms.TextInput(
                attrs={"placeholder": "Nombre de la mascota"}
            ),
            "raza": forms.TextInput(
                attrs={"placeholder": "Ejemplo: Labrador"}
            ),
            "fecha_nacimiento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),
            "color": forms.TextInput(
                attrs={"placeholder": "Color de la mascota"}
            ),
            "microchip": forms.TextInput(
                attrs={"placeholder": "Numero de microchip (opcional)"}
            ),
            "peso": forms.NumberInput(
                attrs={"step": "0.01", "min": "0.01"}
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Observaciones generales del paciente"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["tutor"].queryset = Tutor.objects.filter(
            activo=True
        ).order_by("nombre", "apellido")

        # Permitir conservar un tutor inactivo al editar
        # una mascota que ya lo tiene asociado.
        if self.instance.pk and self.instance.tutor_id:
            self.fields["tutor"].queryset = Tutor.objects.filter(
                pk=self.instance.tutor_id
            ) | Tutor.objects.filter(activo=True)

        self.fields["tutor"].empty_label = "Seleccione un tutor"

        self.fields["fecha_nacimiento"].input_formats = [
            "%Y-%m-%d"
        ]

        for nombre, campo in self.fields.items():
            if nombre == "activo":
                campo.widget.attrs["class"] = "mascota-v16-check"
            else:
                campo.widget.attrs["class"] = "mascota-v16-input"

    def clean_microchip(self):
        microchip = self.cleaned_data.get("microchip")

        if not microchip:
            return None

        return microchip.strip() or None


# PETCARE_PASO_112_FORMULARIO_SOLICITUD

class SolicitudMascotaForm(forms.ModelForm):

    class Meta:
        model = SolicitudMascota

        fields = [
            "tipo",
            "nombre",
            "especie",
            "raza",
            "sexo",
            "microchip",
            "informacion_adicional",
        ]

        widgets = {
            "informacion_adicional": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Indique antecedentes que ayuden "
                        "a verificar la solicitud."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for campo in self.fields.values():
            campo.widget.attrs["class"] = (
                "petcare-solicitud-input"
            )

    def clean_microchip(self):
        valor = self.cleaned_data.get("microchip", "")
        return valor.strip()
