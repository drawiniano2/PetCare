from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings


def validar_rut_chileno(valor):
    rut = valor.upper().replace(".", "").replace("-", "").strip()

    if len(rut) < 2 or not rut[:-1].isdigit():
        raise ValidationError("Ingrese un RUT chileno válido.")

    numero = rut[:-1]
    verificador = rut[-1]

    if not (7 <= len(numero) <= 8):
        raise ValidationError("El RUT debe tener 7 u 8 dígitos.")

    suma = 0
    multiplicador = 2

    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resultado = 11 - (suma % 11)
    esperado = "0" if resultado == 11 else "K" if resultado == 10 else str(resultado)

    if verificador != esperado:
        raise ValidationError("El dígito verificador del RUT es incorrecto.")


class Tutor(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfil_tutor",
        verbose_name="Cuenta de usuario",
    )

    rut = models.CharField(
        max_length=12,
        unique=True,
        validators=[validar_rut_chileno],
        verbose_name="RUT",
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField(verbose_name="Correo electrónico")
    direccion = models.CharField(max_length=255, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tutor"
        verbose_name_plural = "Tutores"
        ordering = ["apellido", "nombre"]

    def clean(self):
        super().clean()
        if self.rut:
            self.rut = self.rut.upper().replace(".", "").replace("-", "").strip()
            validar_rut_chileno(self.rut)

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.rut}"
