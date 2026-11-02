from django import forms

from .models import Tutor


class TutorForm(forms.ModelForm):
    class Meta:
        model = Tutor

        fields = [
            "rut",
            "nombre",
            "apellido",
            "telefono",
            "correo",
            "direccion",
            "activo",
        ]

        labels = {
            "rut": "RUT chileno",
            "nombre": "Nombre",
            "apellido": "Apellido",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
            "direccion": "Dirección",
            "activo": "Tutor activo",
        }

        widgets = {
            "rut": forms.TextInput(attrs={
                "placeholder": "Ejemplo: 12345678-5",
                "autocomplete": "off",
            }),
            "nombre": forms.TextInput(attrs={
                "placeholder": "Ingrese el nombre",
            }),
            "apellido": forms.TextInput(attrs={
                "placeholder": "Ingrese el apellido",
            }),
            "telefono": forms.TextInput(attrs={
                "placeholder": "Ejemplo: +56912345678",
            }),
            "correo": forms.EmailInput(attrs={
                "placeholder": "correo@ejemplo.cl",
            }),
            "direccion": forms.TextInput(attrs={
                "placeholder": "Dirección del tutor",
            }),
        }
