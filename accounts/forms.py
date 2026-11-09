from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from tutores.models import Tutor, validar_rut_chileno


User = get_user_model()


class RegistroTutorForm(UserCreationForm):
    username = forms.RegexField(
        regex=r"^[A-Za-z0-9._-]+$",
        min_length=4,
        max_length=30,
        label="Nombre de usuario",
        help_text=(
            "Entre 4 y 30 caracteres. Utiliza letras, "
            "números, puntos, guiones o guiones bajos."
        ),
        error_messages={
            "invalid": (
                "Utiliza solo letras, números, "
                "puntos, guiones o guiones bajos."
            ),
            "min_length": "Debe tener al menos 4 caracteres.",
            "max_length": "No puede superar 30 caracteres.",
        },
        widget=forms.TextInput(attrs={
            "autocomplete": "username",
            "maxlength": "30",
            "minlength": "4",
        }),
    )

    rut = forms.CharField(
        max_length=12,
        label="RUT chileno",
        widget=forms.TextInput(attrs={
            "placeholder": "12345678-5",
            "autocomplete": "off",
        }),
    )
    nombre = forms.CharField(
        max_length=100,
        label="Nombre",
        widget=forms.TextInput(attrs={
            "autocomplete": "given-name",
        }),
    )
    apellido = forms.CharField(
        max_length=100,
        label="Apellido",
        widget=forms.TextInput(attrs={
            "autocomplete": "family-name",
        }),
    )
    telefono = forms.CharField(
        max_length=20,
        label="Teléfono",
        widget=forms.TextInput(attrs={
            "autocomplete": "tel",
        }),
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
        }),
    )
    direccion = forms.CharField(
        max_length=255,
        required=False,
        label="Dirección",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        rut = rut.upper().replace(".", "").replace("-", "").strip()

        validar_rut_chileno(rut)

        if Tutor.objects.filter(rut__iexact=rut).exists():
            raise ValidationError(
                "Este RUT ya se encuentra registrado. "
                "Solicite asistencia para vincular su cuenta."
            )

        return rut

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()

        if User.objects.filter(email__iexact=correo).exists():
            raise ValidationError(
                "Este correo ya se encuentra registrado."
            )

        if Tutor.objects.filter(correo__iexact=correo).exists():
            raise ValidationError(
                "Este correo ya pertenece a una ficha de tutor. "
                "Solicite asistencia para vincular su cuenta."
            )

        return correo

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        return username


# PETCARE_FORM_SOLICITUD_ACCESO_165R355

from accounts.models import SolicitudAcceso


class SolicitudAccesoForm(forms.ModelForm):

    class Meta:
        model = SolicitudAcceso
        fields = (
            "tipo_cuenta",
            "nombre",
            "apellido",
            "rut",
            "correo",
            "telefono",
            "username_solicitado",
        )

        labels = {
            "tipo_cuenta": "Tipo de cuenta solicitada",
            "nombre": "Nombre",
            "apellido": "Apellido",
            "rut": "RUT chileno",
            "correo": "Correo electrónico",
            "telefono": "Teléfono",
            "username_solicitado": "Nombre de usuario solicitado",
        }

        widgets = {
            "tipo_cuenta": forms.Select(),
            "nombre": forms.TextInput(
                attrs={"autocomplete": "given-name"}
            ),
            "apellido": forms.TextInput(
                attrs={"autocomplete": "family-name"}
            ),
            "rut": forms.TextInput(
                attrs={"placeholder": "12345678-5"}
            ),
            "correo": forms.EmailInput(
                attrs={"autocomplete": "email"}
            ),
            "telefono": forms.TextInput(
                attrs={"autocomplete": "tel"}
            ),
            "username_solicitado": forms.TextInput(
                attrs={"autocomplete": "username"}
            ),
        }

    def clean_rut(self):
        rut = (
            self.cleaned_data["rut"]
            .upper()
            .replace(".", "")
            .replace("-", "")
            .strip()
        )

        validar_rut_chileno(rut)

        if Tutor.objects.filter(rut__iexact=rut).exists():
            raise ValidationError(
                "Este RUT ya está registrado como tutor."
            )

        if SolicitudAcceso.objects.filter(
            rut__iexact=rut,
            estado__in=["PENDIENTE", "APROBADA"],
        ).exists():
            raise ValidationError(
                "Ya existe una solicitud vigente para este RUT."
            )

        return rut

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()

        if User.objects.filter(email__iexact=correo).exists():
            raise ValidationError(
                "Este correo ya pertenece a una cuenta."
            )

        if SolicitudAcceso.objects.filter(
            correo__iexact=correo,
            estado__in=["PENDIENTE", "APROBADA"],
        ).exists():
            raise ValidationError(
                "Ya existe una solicitud vigente con este correo."
            )

        return correo

    def clean_username_solicitado(self):
        username = (
            self.cleaned_data["username_solicitado"].strip()
        )

        if len(username) < 4:
            raise ValidationError(
                "El nombre de usuario debe tener al menos 4 caracteres."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        if SolicitudAcceso.objects.filter(
            username_solicitado__iexact=username,
            estado__in=["PENDIENTE", "APROBADA"],
        ).exists():
            raise ValidationError(
                "Este nombre de usuario ya está solicitado."
            )

        return username
