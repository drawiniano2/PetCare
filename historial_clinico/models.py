from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class FichaClinica(models.Model):
    mascota = models.OneToOneField(
        "mascotas.Mascota",
        on_delete=models.PROTECT,
        related_name="ficha_clinica",
    )
    antecedentes = models.TextField(blank=True)
    alergias = models.TextField(blank=True)
    enfermedades_previas = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha clinica"
        verbose_name_plural = "Fichas clinicas"
        ordering = ["mascota__nombre"]

    def __str__(self):
        return f"Ficha clinica - {self.mascota.nombre}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AtencionClinica(models.Model):
    ficha = models.ForeignKey(
        FichaClinica,
        on_delete=models.PROTECT,
        related_name="atenciones",
    )
    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        related_name="atenciones_clinicas",
    )
    cita = models.OneToOneField(
        "citas.Cita",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="atencion_clinica",
    )
    fecha_atencion = models.DateTimeField(default=timezone.now)
    motivo_consulta = models.TextField()
    sintomas = models.TextField(blank=True)
    diagnostico = models.TextField(blank=True)
    tratamiento = models.TextField(blank=True)
    indicaciones = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Atencion clinica"
        verbose_name_plural = "Atenciones clinicas"
        ordering = ["-fecha_atencion", "-id"]

    def __str__(self):
        return (
            f"Atencion de {self.ficha.mascota.nombre} "
            f"- {self.fecha_atencion:%d/%m/%Y}"
        )

    def clean(self):
        super().clean()

        errores = {}

        if self.cita_id and self.ficha_id and self.veterinario_id:
            if self.cita.mascota_id != self.ficha.mascota_id:
                errores["cita"] = (
                    "La cita no corresponde a la mascota de la ficha."
                )

            if self.cita.veterinario_id != self.veterinario_id:
                errores["veterinario"] = (
                    "El veterinario debe coincidir con el de la cita."
                )

            if self.cita.estado != "COMPLETADA":
                errores["cita"] = (
                    "La cita debe estar COMPLETADA para registrar "
                    "una atencion clinica."
                )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# PETCARE V20 - RECETAS VETERINARIAS

class RecetaVeterinaria(models.Model):
    atencion = models.ForeignKey(
        "historial_clinico.AtencionClinica",
        on_delete=models.PROTECT,
        related_name="recetas",
    )

    fecha_emision = models.DateTimeField(
        default=timezone.now,
    )

    indicaciones_generales = models.TextField(
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha_emision", "-id"]
        verbose_name = "Receta veterinaria"
        verbose_name_plural = "Recetas veterinarias"

    def __str__(self):
        return f"Receta N.{self.pk} - Atencion {self.atencion_id}"


class MedicamentoRecetado(models.Model):
    receta = models.ForeignKey(
        "historial_clinico.RecetaVeterinaria",
        on_delete=models.CASCADE,
        related_name="medicamentos",
    )

    nombre = models.CharField(
        max_length=200,
    )

    presentacion = models.CharField(
        max_length=150,
        blank=True,
    )

    dosis = models.CharField(
        max_length=150,
    )

    via_administracion = models.CharField(
        max_length=100,
    )

    frecuencia = models.CharField(
        max_length=150,
    )

    duracion = models.CharField(
        max_length=150,
    )

    instrucciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Medicamento recetado"
        verbose_name_plural = "Medicamentos recetados"

    def __str__(self):
        return self.nombre
