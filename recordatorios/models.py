from django.db import models


class Vacuna(models.Model):
    ficha = models.ForeignKey(
        "historial_clinico.FichaClinica",
        on_delete=models.PROTECT,
        related_name="vacunas",
    )
    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        related_name="vacunas_aplicadas",
    )
    nombre = models.CharField(max_length=150)
    fecha_aplicacion = models.DateField()
    proxima_dosis = models.DateField(null=True, blank=True)
    lote = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_aplicacion", "-id"]
        verbose_name = "Vacuna"
        verbose_name_plural = "Vacunas"

    def __str__(self):
        return f"{self.nombre} - {self.ficha.mascota.nombre}"


class ControlVeterinario(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        REALIZADO = "Realizado", "Realizado"
        CANCELADO = "Cancelado", "Cancelado"

    ficha = models.ForeignKey(
        "historial_clinico.FichaClinica",
        on_delete=models.PROTECT,
        related_name="controles_programados",
    )
    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        related_name="controles_programados",
    )
    motivo = models.CharField(max_length=250)
    fecha_programada = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_programada", "id"]
        verbose_name = "Control veterinario"
        verbose_name_plural = "Controles veterinarios"

    def __str__(self):
        return f"{self.ficha.mascota.nombre} - {self.fecha_programada}"
