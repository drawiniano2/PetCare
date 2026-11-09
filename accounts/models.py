from django.db import models

# Create your models here.


# PETCARE_SOLICITUD_ACCESO_165R351

from django.conf import settings
from django.core.validators import RegexValidator
from tutores.models import validar_rut_chileno


class SolicitudAcceso(models.Model):

    class TipoCuenta(models.TextChoices):
        VETERINARIO = "VETERINARIO", "Veterinario"
        PERSONAL = "PERSONAL", "Personal autorizado"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    rut = models.CharField(
        max_length=12,
        validators=[validar_rut_chileno],
    )

    correo = models.EmailField()
    telefono = models.CharField(max_length=20)

    username_solicitado = models.CharField(
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9._-]+$",
                message="Nombre de usuario no válido.",
            )
        ],
    )

    tipo_cuenta = models.CharField(
        max_length=20,
        choices=TipoCuenta.choices,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )

    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
    )

    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_acceso_revisadas",
    )

    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    usuario_creado = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitud_acceso_origen",
    )

    # PETCARE_PASSWORD_TEMPORAL_165R424
    cambio_password_obligatorio = models.BooleanField(
        default=False,
        verbose_name="Cambio de contraseña obligatorio",
    )

    class Meta:
        verbose_name = "Solicitud de acceso"
        verbose_name_plural = "Solicitudes de acceso"
        ordering = ["-fecha_solicitud"]

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
        return (
            f"{self.nombre} {self.apellido} - "
            f"{self.get_tipo_cuenta_display()} - "
            f"{self.get_estado_display()}"
        )
