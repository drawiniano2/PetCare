from django.conf import settings
from django.db import models
from tutores.models import validar_rut_chileno


class Veterinario(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfil_veterinario',
        verbose_name='Cuenta de usuario',
    )

    rut = models.CharField(
        max_length=12,
        unique=True,
        validators=[validar_rut_chileno],
        verbose_name="RUT",
    )

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    especialidad = models.CharField(
        max_length=150,
        default="Medicina veterinaria general",
    )

    numero_registro = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numero de registro profesional",
    )

    telefono = models.CharField(max_length=20)

    correo = models.EmailField(
        verbose_name="Correo electr\u00f3nico",
    )

    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Veterinario"
        verbose_name_plural = "Veterinarios"
        ordering = ["apellido", "nombre"]

    def clean(self):
        super().clean()

        if self.rut:
            self.rut = (
                self.rut.upper()
                .replace(".", "")
                .replace("-", "")
                .strip()
            )
            validar_rut_chileno(self.rut)

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.especialidad}"
