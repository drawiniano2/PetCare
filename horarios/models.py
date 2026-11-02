from django.core.exceptions import ValidationError
from django.db import models


class Horario(models.Model):

    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        related_name="horarios",
    )

    dia_semana = models.IntegerField(
        choices=DiaSemana.choices,
        verbose_name="Día de la semana",
    )

    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        super().clean()

        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValidationError({
                    "hora_fin": (
                        "La hora de término debe ser "
                        "posterior a la hora de inicio."
                    )
                })

        if (
            self.activo
            and self.veterinario_id
            and self.dia_semana is not None
            and self.hora_inicio
            and self.hora_fin
        ):
            conflictos = Horario.objects.filter(
                veterinario_id=self.veterinario_id,
                dia_semana=self.dia_semana,
                activo=True,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio,
            )

            if self.pk:
                conflictos = conflictos.exclude(pk=self.pk)

            if conflictos.exists():
                raise ValidationError(
                    "El veterinario ya tiene un horario "
                    "activo superpuesto para este día."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.veterinario} - "
            f"{self.get_dia_semana_display()} "
            f"{self.hora_inicio:%H:%M} a "
            f"{self.hora_fin:%H:%M}"
        )
