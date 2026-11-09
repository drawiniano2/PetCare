from tutores.models import validar_rut_chileno
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

    # PETCARE 165R.357.9.189 - VETERINARIO OPCIONAL
    veterinario = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="citas",
    )


    # PETCARE 165R.357.9.182 - SERVICIO Y PERSONAL EN CITA
    servicio = models.ForeignKey(
        "citas.Servicio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="citas",
    )

    personal_servicio = models.ForeignKey(
        "citas.PersonalServicio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
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

    # PETCARE 165R.357.9.193 - VALIDACION DOBLE CIRCUITO
    def clean(self):
        super().clean()

        errores = {}

        servicio = self.servicio if self.servicio_id else None
        es_estetica = (
            servicio is not None
            and servicio.categoria == "ESTETICA"
        )

        if servicio is not None and servicio.categoria not in (
            "MEDICO", "ESTETICA"
        ):
            errores["servicio"] = "Categoria no reconocida."

        if es_estetica:
            if self.veterinario_id:
                errores["veterinario"] = (
                    "Una cita de estetica no requiere veterinario."
                )
            if not self.personal_servicio_id:
                errores["personal_servicio"] = (
                    "Seleccione personal de estetica."
                )
        else:
            if not self.veterinario_id:
                errores["veterinario"] = (
                    "Seleccione un veterinario."
                )
            if self.personal_servicio_id:
                errores["personal_servicio"] = (
                    "El personal de estetica no corresponde "
                    "a una cita medica."
                )

        if self.duracion_minutos is not None:
            if self.duracion_minutos <= 0:
                errores["duracion_minutos"] = (
                    "La duracion debe ser positiva."
                )

        if self.estado != self.Estado.CANCELADA:
            if self.mascota_id:
                from mascotas.models import Mascota
                if Mascota.objects.filter(
                    pk=self.mascota_id, activo=False
                ).exists():
                    errores["mascota"] = (
                        "No se permiten citas para mascotas inactivas."
                    )

            if servicio is not None and not servicio.activo:
                errores["servicio"] = "El servicio esta inactivo."

            if es_estetica and self.personal_servicio_id:
                from citas.models import PersonalServicio
                if PersonalServicio.objects.filter(
                    pk=self.personal_servicio_id, activo=False
                ).exists():
                    errores["personal_servicio"] = (
                        "El personal seleccionado esta inactivo."
                    )

            if not es_estetica and self.veterinario_id:
                from veterinarios.models import Veterinario
                if Veterinario.objects.filter(
                    pk=self.veterinario_id, activo=False
                ).exists():
                    errores["veterinario"] = (
                        "El veterinario seleccionado esta inactivo."
                    )

        if errores:
            raise ValidationError(errores)

        if not (
            self.fecha and self.hora_inicio
            and self.duracion_minutos is not None
        ):
            return

        inicio = datetime.combine(self.fecha, self.hora_inicio)
        fin = inicio + timedelta(minutes=self.duracion_minutos)

        if fin.date() != self.fecha:
            raise ValidationError(
                "La cita no puede terminar en otro dia."
            )

        if self.estado == self.Estado.CANCELADA:
            return

        dia = self.fecha.weekday()

        if es_estetica:
            from citas.models import HorarioPersonalServicio
            horarios = HorarioPersonalServicio.objects.filter(
                personal_id=self.personal_servicio_id,
                dia_semana=dia,
                activo=True,
            )
            conflictos = type(self).objects.filter(
                personal_servicio_id=self.personal_servicio_id,
                fecha=self.fecha,
            )
            profesional = "El personal"
        else:
            from horarios.models import Horario
            horarios = Horario.objects.filter(
                veterinario_id=self.veterinario_id,
                dia_semana=dia,
                activo=True,
            )
            conflictos = type(self).objects.filter(
                veterinario_id=self.veterinario_id,
                fecha=self.fecha,
            )
            profesional = "El veterinario"

        disponible = any(
            h.hora_inicio <= inicio.time()
            and fin.time() <= h.hora_fin
            for h in horarios
        )

        if not disponible:
            raise ValidationError(
                "La cita esta fuera del horario del profesional."
            )

        conflictos = conflictos.exclude(
            estado=self.Estado.CANCELADA
        )

        if self.pk:
            conflictos = conflictos.exclude(pk=self.pk)

        for otra in conflictos:
            otro_inicio = datetime.combine(
                otra.fecha, otra.hora_inicio
            )
            otro_fin = otro_inicio + timedelta(
                minutes=otra.duracion_minutos
            )

            if inicio < otro_fin and fin > otro_inicio:
                raise ValidationError(
                    profesional + " ya tiene una cita superpuesta."
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.veterinario_id:
                from veterinarios.models import Veterinario
                Veterinario.objects.select_for_update().get(
                    pk=self.veterinario_id
                )

            if self.personal_servicio_id:
                from citas.models import PersonalServicio
                PersonalServicio.objects.select_for_update().get(
                    pk=self.personal_servicio_id
                )

            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        profesional = (
            self.veterinario
            if self.veterinario_id
            else self.personal_servicio
        )
        return (
            f"{self.mascota.nombre} - "
            f"{profesional} - "
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

    # PETCARE 165R.352.70 - VETERINARIO PREFERIDO
    veterinario_preferido = models.ForeignKey(
        "veterinarios.Veterinario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_preferidas",
        verbose_name="Veterinario preferido",
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


# PETCARE 165R.357.9.172 - CATALOGO SERVICIOS
class Servicio(models.Model):

    class Categoria(models.TextChoices):
        MEDICO = "MEDICO", "Servicio médico"
        ESTETICA = "ESTETICA", "Estética e higiene"

    nombre = models.CharField(
        max_length=120,
        unique=True,
    )

    categoria = models.CharField(
        max_length=15,
        choices=Categoria.choices,
    )

    duracion_minutos = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración estimada (minutos)",
    )

    activo = models.BooleanField(default=True)

    # PETCARE 165R.357.9.238 - PRECIO OPCIONAL CLP
    precio = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Precio (CLP)",
    )

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["categoria", "nombre"]

    def clean(self):
        super().clean()

        if not 1 <= self.duracion_minutos <= 480:
            raise ValidationError({
                "duracion_minutos":
                    "La duración debe estar entre 1 y 480 minutos."
            })

    def __str__(self):
        return self.nombre


# PETCARE 165R.357.9.176 - PERSONAL SERVICIOS
class PersonalServicio(models.Model):

    # PETCARE 165R.357.9.226 - RUT VERIFICADO
    rut = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_rut_chileno],
        verbose_name="RUT",
    )

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    especialidad = models.CharField(
        max_length=120,
        default="Estética e higiene animal",
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
    )

    correo = models.EmailField(
        blank=True,
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Personal de servicio"
        verbose_name_plural = "Personal de servicios"
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
        else:
            self.rut = None

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.especialidad}"


# PETCARE 165R.357.9.178 - HORARIOS PERSONAL
class HorarioPersonalServicio(models.Model):

    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    personal = models.ForeignKey(
        "citas.PersonalServicio",
        on_delete=models.PROTECT,
        related_name="horarios",
    )

    dia_semana = models.IntegerField(
        choices=DiaSemana.choices,
    )

    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Horario de personal"
        verbose_name_plural = "Horarios de personal"
        ordering = ["dia_semana", "hora_inicio"]

    def clean(self):
        super().clean()

        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValidationError(
                    "La hora de término debe ser "
                    "posterior a la hora de inicio."
                )

        if (
            self.activo
            and self.personal_id
            and self.dia_semana is not None
            and self.hora_inicio
            and self.hora_fin
        ):
            conflictos = type(self).objects.filter(
                personal_id=self.personal_id,
                dia_semana=self.dia_semana,
                activo=True,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio,
            )

            if self.pk:
                conflictos = conflictos.exclude(pk=self.pk)

            if conflictos.exists():
                raise ValidationError(
                    "El personal ya tiene un horario "
                    "superpuesto para este día."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.personal} - "
            f"{self.get_dia_semana_display()} "
            f"{self.hora_inicio:%H:%M} a "
            f"{self.hora_fin:%H:%M}"
        )
