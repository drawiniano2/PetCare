from django import forms

from veterinarios.models import Veterinario
from .models import Horario


class HorarioForm(forms.ModelForm):

    class Meta:
        model = Horario

        fields = [
            "veterinario",
            "dia_semana",
            "hora_inicio",
            "hora_fin",
            "activo",
        ]

        widgets = {
            "veterinario": forms.Select(),
            "dia_semana": forms.Select(),
            "hora_inicio": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time"}
            ),
            "hora_fin": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time"}
            ),
            "activo": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["veterinario"].queryset = (
            Veterinario.objects.filter(activo=True)
        )

        self.fields["veterinario"].empty_label = (
            "Seleccione un veterinario"
        )

        self.fields["dia_semana"].choices = [
            ("", "Seleccione un día"),
            *Horario.DiaSemana.choices,
        ]

        self.fields["hora_inicio"].input_formats = ["%H:%M"]
        self.fields["hora_fin"].input_formats = ["%H:%M"]

        self.fields["hora_inicio"].label = "Hora de inicio"
        self.fields["hora_fin"].label = "Hora de término"
