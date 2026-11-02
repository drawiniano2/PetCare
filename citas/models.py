from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Cita(models.Model):

    class Estado(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    mascota = models.ForeignKey(
        "mascotas.Mascota",
        on_delete=models.PROTECT,
        related_name="citas",
    )

    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        related_name="citas",
    )

    fecha = models.DateField()
    hora_inicio = models.TimeField()

    duracion_minutos = models.PositiveIntegerField(
        default=30,
        verbose_name="Duracion (minutos)",
    )

    motivo = models.TextField()

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PROGRAMADA,
    )

    observaciones = models.TextField(blank=True)
    archivada = models.BooleanField(
        default=False,
        verbose_name="Archivada",
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["fecha", "hora_inicio"]

    def clean(self):
        super().clean()

        if self.estado != self.Estado.CANCELADA:
            if self.mascota_id:
                from mascotas.models import Mascota

                if Mascota.objects.filter(
                    pk=self.mascota_id,
                    activo=False,
                ).exists():
                    raise ValidationError({
                        "mascota": "No se pueden programar citas "
                        "para una mascota inactiva."
                    })

            if self.veterinario_id:
                from veterinarios.models import Veterinario

                if Veterinario.objects.filter(
                    pk=self.veterinario_id,
                    activo=False,
                ).exists():
                    raise ValidationError({
                        "veterinario": "No se pueden programar citas "
                        "con un veterinario inactivo."
                    })

        if not (
            self.fecha
            and self.hora_inicio
            and self.duracion_minutos is not None
            and self.veterinario_id
        ):
            return

        if self.duracion_minutos <= 0:
            raise ValidationError({
                "duracion_minutos": "La duracion debe ser positiva."
            })

        inicio = datetime.combine(
            self.fecha,
            self.hora_inicio,
        )

        fin = inicio + timedelta(
            minutes=self.duracion_minutos
        )

        if fin.date() != self.fecha:
            raise ValidationError(
                "La cita no puede terminar en otro dia."
            )

        if self.estado == self.Estado.CANCELADA:
            return

        from horarios.models import Horario

        dia = self.fecha.weekday()

        horarios = Horario.objects.filter(
            veterinario_id=self.veterinario_id,
            dia_semana=dia,
            activo=True,
        )

        disponible = any(
            horario.hora_inicio <= inicio.time()
            and fin.time() <= horario.hora_fin
            for horario in horarios
        )

        if not disponible:
            raise ValidationError(
                "La cita esta fuera del horario de atencion "
                "del veterinario."
            )

        conflictos = Cita.objects.filter(
            veterinario_id=self.veterinario_id,
            fecha=self.fecha,
        ).exclude(
            estado=self.Estado.CANCELADA
        )

        if self.pk:
            conflictos = conflictos.exclude(pk=self.pk)

        for otra in conflictos:
            otro_inicio = datetime.combine(
                otra.fecha,
                otra.hora_inicio,
            )
            otro_fin = otro_inicio + timedelta(
                minutes=otra.duracion_minutos
            )

            if inicio < otro_fin and fin > otro_inicio:
                raise ValidationError(
                    "El veterinario ya tiene una cita "
                    "superpuesta en este horario."
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.veterinario_id:
                from veterinarios.models import Veterinario

                Veterinario.objects.select_for_update().get(
                    pk=self.veterinario_id
                )

            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.mascota.nombre} - "
            f"{self.veterinario} - "
            f"{self.fecha} {self.hora_inicio:%H:%M}"
        )


# PETCARE_SOLICITUD_CITA_165E
class SolicitudCita(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        CANCELADA = "CANCELADA", "Cancelada"

    tutor = models.ForeignKey(
        "tutores.Tutor",
        on_delete=models.PROTECT,
        related_name="solicitudes_citas",
    )

    mascota = models.ForeignKey(
        "mascotas.Mascota",
        on_delete=models.PROTECT,
        related_name="solicitudes_citas",
    )

    fecha_preferida = models.DateField()

    hora_preferida = models.TimeField()

    motivo = models.TextField()

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    cita = models.OneToOneField(
        "citas.Cita",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitud_origen",
    )

    observaciones_clinica = models.TextField(
        blank=True,
    )

    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
    )

    def clean(self):
        super().clean()

        from django.core.exceptions import ValidationError

        errores = {}

        if self.tutor_id and self.mascota_id:
            if self.mascota.tutor_id != self.tutor_id:
                errores["mascota"] = (
                    "La mascota no pertenece al tutor indicado."
                )

        if self.cita_id and self.mascota_id:
            if self.cita.mascota_id != self.mascota_id:
                errores["cita"] = (
                    "La cita no corresponde a la mascota."
                )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Solicitud {self.pk or 'nueva'} - "
            f"{self.mascota} - {self.get_estado_display()}"
        )

    class Meta:
        ordering = ["-fecha_solicitud"]
        verbose_name = "Solicitud de cita"
        verbose_name_plural = "Solicitudes de citas"
