from django import forms

from .models import Veterinario


class VeterinarioForm(forms.ModelForm):

    class Meta:
        model = Veterinario

        fields = [
            "rut",
            "nombre",
            "apellido",
            "especialidad",
            "numero_registro",
            "telefono",
            "correo",
            "activo",
        ]

        widgets = {
            "rut": forms.TextInput(attrs={
                "placeholder": "Ej.: 12345678-5",
                "autocomplete": "off",
            }),
            "nombre": forms.TextInput(attrs={
                "placeholder": "Nombre del profesional",
            }),
            "apellido": forms.TextInput(attrs={
                "placeholder": "Apellido del profesional",
            }),
            "especialidad": forms.TextInput(attrs={
                "placeholder": "Ej.: Medicina veterinaria general",
            }),
            "numero_registro": forms.TextInput(attrs={
                "placeholder": "Número de registro profesional",
            }),
            "telefono": forms.TextInput(attrs={
                "placeholder": "Ej.: 912345678",
            }),
            "correo": forms.EmailInput(attrs={
                "placeholder": "correo@ejemplo.com",
            }),
            "activo": forms.CheckboxInput(),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get("rut", "")
        return rut.upper().replace(".", "").replace("-", "").strip()

    def clean_numero_registro(self):
        registro = self.cleaned_data.get("numero_registro", "")
        return registro.strip()
