from django import forms

from .models import Cita
from mascotas.models import Mascota
from veterinarios.models import Veterinario


class CitaForm(forms.ModelForm):

    class Meta:
        model = Cita

        fields = [
            "mascota",
            "veterinario",
            "fecha",
            "hora_inicio",
            "duracion_minutos",
            "motivo",
            "observaciones",
        ]

        widgets = {
            "fecha": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "hora_inicio": forms.Select(
                attrs={"data-disponibilidad": "horas"},
                choices=[("", "Seleccione veterinario y fecha")],
            ),
            "duracion_minutos": forms.NumberInput(
                attrs={"min": 1, "step": 1},
            ),
            "motivo": forms.Textarea(
                attrs={"rows": 3},
            ),
            "observaciones": forms.Textarea(
                attrs={"rows": 3},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["mascota"].queryset = (
            Mascota.objects.filter(
                activo=True,
                tutor__activo=True,
            ).select_related("tutor")
        )

        self.fields["veterinario"].queryset = (
            Veterinario.objects.filter(activo=True)
        )

        self.fields["mascota"].empty_label = (
            "Seleccione una mascota"
        )

        self.fields["veterinario"].empty_label = (
            "Seleccione un veterinario"
        )

        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["hora_inicio"].input_formats = ["%H:%M"]

        self.fields["fecha"].label = "Fecha de la cita"
        self.fields["hora_inicio"].label = "Hora de inicio"
        self.fields["duracion_minutos"].label = 'Duración (minutos)'
        self.fields["motivo"].label = "Motivo de la consulta"
        self.fields["observaciones"].label = "Observaciones"

        self.fields["observaciones"].required = False


        # PETCARE_HORA_INICIAL_165R231F
        if not self.is_bound and self.instance.pk:
            if self.instance.hora_inicio:
                self.initial["hora_inicio"] = (
                    self.instance.hora_inicio.strftime("%H:%M")
                )


        # PETCARE_FORMATO_SELECT_165R231I
        from datetime import time as tipo_hora
        from types import MethodType

        campo_hora = self.fields["hora_inicio"]

        def preparar_hora(campo, valor):
            if isinstance(valor, tipo_hora):
                return valor.strftime("%H:%M")
            return valor

        campo_hora.prepare_value = MethodType(
            preparar_hora,
            campo_hora
        )

        # PETCARE_HORAS_DINAMICAS_165R230Y
        from datetime import date
        from .disponibilidad import obtener_horas_disponibles

        datos = self.data if self.is_bound else self.initial

        veterinario_id = datos.get("veterinario")
        fecha_texto = datos.get("fecha")
        duracion = datos.get("duracion_minutos", 30)

        if not self.is_bound and self.instance.pk:
            veterinario_id = self.instance.veterinario_id
            fecha_texto = self.instance.fecha
            duracion = self.instance.duracion_minutos

        opciones = [("", "Seleccione una hora disponible")]

        try:
            if isinstance(fecha_texto, date):
                fecha = fecha_texto
            else:
                fecha = date.fromisoformat(str(fecha_texto))

            horas = obtener_horas_disponibles(
                veterinario_id,
                fecha,
                duracion,
                excluir_cita_id=self.instance.pk,
            )

            opciones.extend((hora, hora) for hora in horas)

            if not self.is_bound and self.instance.pk:
                actual = self.instance.hora_inicio.strftime("%H:%M")
                if actual not in horas:
                    opciones.append((actual, actual + " (hora actual)"))

        except (ValueError, TypeError):
            pass

        self.fields["hora_inicio"].widget.choices = opciones



# PETCARE_SOLICITUD_CITA_FORM_165J
from datetime import date
from .models import SolicitudCita


class SolicitudCitaForm(forms.ModelForm):

    class Meta:
        model = SolicitudCita

        fields = [
            "mascota",
            "fecha_preferida",
            "hora_preferida",
            "motivo",
        ]

        widgets = {
            "fecha_preferida": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "hora_preferida": forms.TimeInput(
                format="%H:%M",
                attrs={"type": "time"},
            ),
            "motivo": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Describa brevemente el motivo "
                        "de la consulta veterinaria"
                    ),
                },
            ),
        }

    def __init__(self, *args, tutor=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.tutor = tutor

        self.fields["mascota"].queryset = (
            Mascota.objects.filter(
                tutor=tutor,
                activo=True,
            )
            if tutor is not None
            else Mascota.objects.none()
        )

        self.fields["mascota"].empty_label = (
            "Seleccione su mascota"
        )

        self.fields["fecha_preferida"].input_formats = [
            "%Y-%m-%d"
        ]

        self.fields["hora_preferida"].input_formats = [
            "%H:%M"
        ]

        self.fields["mascota"].label = "Mascota"
        self.fields["fecha_preferida"].label = (
            "Fecha preferida"
        )
        self.fields["hora_preferida"].label = (
            "Hora preferida"
        )
        self.fields["motivo"].label = (
            "Motivo de la consulta"
        )

        self.fields["fecha_preferida"].widget.attrs[
            "min"
        ] = date.today().isoformat()

    def clean_fecha_preferida(self):
        fecha = self.cleaned_data["fecha_preferida"]

        if fecha < date.today():
            raise forms.ValidationError(
                "No puede solicitar una fecha anterior a hoy."
            )

        return fecha

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()

        if not motivo:
            raise forms.ValidationError(
                "Debe indicar el motivo de la consulta."
            )

        return motivo

    def save(self, commit=True):
        if self.tutor is None:
            raise ValueError(
                "Se requiere un tutor para guardar."
            )

        solicitud = super().save(commit=False)
        solicitud.tutor = self.tutor
        solicitud.estado = SolicitudCita.Estado.PENDIENTE

        if commit:
            solicitud.save()
            self.save_m2m()

        return solicitud


# PETCARE_EDITAR_SOLICITUD_165R21
class EditarSolicitudCitaForm(SolicitudCitaForm):
    """
    Edicion restringida de solicitudes pendientes.
    No permite modificar mascota, tutor ni estado.
    """

    class Meta(SolicitudCitaForm.Meta):
        fields = [
            "mascota",
            "fecha_preferida",
            "hora_preferida",
            "motivo",
        ]

    def __init__(self, *args, tutor=None, **kwargs):
        super().__init__(*args, tutor=tutor, **kwargs)

        # El formulario original necesita mascota al inicializar.
        # Se retira antes de presentar y validar la edicion.
        self.fields.pop("mascota", None)

        if self.instance.pk:
            if self.instance.tutor_id != getattr(tutor, "pk", None):
                raise ValueError(
                    "La solicitud no pertenece al tutor."
                )

            if (
                self.instance.estado != SolicitudCita.Estado.PENDIENTE
                or self.instance.cita_id is not None
            ):
                raise ValueError(
                    "Solo se pueden editar solicitudes "
                    "pendientes sin cita asociada."
                )

    def save(self, commit=True):
        if not self.instance.pk:
            raise ValueError(
                "Este formulario solo permite editar "
                "solicitudes existentes."
            )

        if (
            self.instance.estado != SolicitudCita.Estado.PENDIENTE
            or self.instance.cita_id is not None
        ):
            raise ValueError(
                "La solicitud ya no puede editarse."
            )

        return super().save(commit=commit)
