from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Mascota(models.Model):

    class Especie(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"
        OTRO = "OTRO", "Otro"

    class Sexo(models.TextChoices):
        MACHO = "M", "Macho"
        HEMBRA = "H", "Hembra"

    tutor = models.ForeignKey(
        "tutores.Tutor",
        on_delete=models.PROTECT,
        related_name="mascotas",
        verbose_name="Tutor responsable",
    )

    nombre = models.CharField(max_length=100)

    especie = models.CharField(
        max_length=10,
        choices=Especie.choices,
    )

    raza = models.CharField(max_length=100, blank=True)

    sexo = models.CharField(
        max_length=1,
        choices=Sexo.choices,
    )

    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
    )

    color = models.CharField(max_length=100, blank=True)

    microchip = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Numero de microchip",
    )

    peso = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        verbose_name="Peso (kg)",
    )

    observaciones = models.TextField(blank=True)

    activo = models.BooleanField(default=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} - {self.tutor}"


# PETCARE_PASO_106_SOLICITUD_MASCOTA

class SolicitudMascota(models.Model):

    class Tipo(models.TextChoices):
        NUEVA = "NUEVA", "Registrar mascota nueva"
        VINCULAR = "VINCULAR", "Vincular mascota existente"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    tutor = models.ForeignKey(
        "tutores.Tutor",
        on_delete=models.PROTECT,
        related_name="solicitudes_mascotas",
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
    )

    nombre = models.CharField(max_length=100)

    especie = models.CharField(
        max_length=10,
        choices=Mascota.Especie.choices,
    )

    raza = models.CharField(max_length=100, blank=True)

    sexo = models.CharField(
        max_length=1,
        choices=Mascota.Sexo.choices,
    )

    microchip = models.CharField(
        max_length=30,
        blank=True,
    )

    informacion_adicional = models.TextField(blank=True)

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
    )

    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_mascotas_revisadas",
    )

    observacion_revision = models.TextField(blank=True)

    class Meta:
        verbose_name = "Solicitud de mascota"
        verbose_name_plural = "Solicitudes de mascotas"
        ordering = ["-fecha_solicitud"]

    def __str__(self):
        return f"{self.nombre} - {self.tutor} - {self.estado}"
