from django import forms

from veterinarios.models import Veterinario


class AprobarSolicitudCitaForm(forms.Form):
    veterinario = forms.ModelChoiceField(
        queryset=Veterinario.objects.none(),
        label="Veterinario asignado",
        empty_label="Seleccione un veterinario",
    )

    duracion_minutos = forms.IntegerField(
        label="Duracion de la consulta (minutos)",
        initial=30,
        min_value=1,
        max_value=480,
    )

    observaciones_clinica = forms.CharField(
        label="Observaciones de la clinica",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["veterinario"].queryset = (
            Veterinario.objects.filter(
                activo=True
            ).order_by("nombre", "apellido")
        )


class RechazarSolicitudCitaForm(forms.Form):
    observaciones_clinica = forms.CharField(
        label="Motivo del rechazo",
        required=True,
        min_length=5,
        widget=forms.Textarea(
            attrs={"rows": 4}
        ),
        help_text=(
            "Explique al tutor por que no "
            "se puede aceptar la solicitud."
        ),
    )

    def clean_observaciones_clinica(self):
        texto = self.cleaned_data[
            "observaciones_clinica"
        ].strip()

        if len(texto) < 5:
            raise forms.ValidationError(
                "Ingrese un motivo de al menos 5 caracteres."
            )

        return texto
