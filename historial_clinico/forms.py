from django import forms

from .models import FichaClinica


class FichaClinicaForm(forms.ModelForm):
    class Meta:
        model = FichaClinica

        fields = [
            "antecedentes",
            "alergias",
            "enfermedades_previas",
            "observaciones",
        ]

        labels = {
            "antecedentes": "Antecedentes generales",
            "alergias": "Alergias conocidas",
            "enfermedades_previas": "Enfermedades previas",
            "observaciones": "Observaciones cl\u00ednicas",
        }

        widgets = {
            campo: forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "pc-campo-clinico",
                }
            )
            for campo in fields
        }


# PETCARE FORMULARIO ATENCION CLINICA V1

from .models import AtencionClinica
from citas.models import Cita
from veterinarios.models import Veterinario


class AtencionClinicaForm(forms.ModelForm):

    class Meta:
        model = AtencionClinica

        fields = [
            "veterinario",
            "cita",
            "fecha_atencion",
            "motivo_consulta",
            "sintomas",
            "diagnostico",
            "tratamiento",
            "indicaciones",
            "observaciones",
        ]

        labels = {
            "veterinario": "Veterinario responsable",
            "cita": "Cita asociada (opcional)",
            "fecha_atencion": "Fecha y hora de atención",
            "motivo_consulta": "Motivo de consulta",
            "sintomas": "Síntomas",
            "diagnostico": "Diagnóstico",
            "tratamiento": "Tratamiento",
            "indicaciones": "Indicaciones",
            "observaciones": "Observaciones adicionales",
        }

        widgets = {
            "fecha_atencion": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "pc-campo-clinico",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "motivo_consulta": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
            "sintomas": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
            "diagnostico": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
            "tratamiento": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
            "indicaciones": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
            "observaciones": forms.Textarea(
                attrs={"rows": 3, "class": "pc-campo-clinico"}
            ),
        }

    def __init__(self, *args, mascota=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.mascota = mascota

        self.fields["veterinario"].queryset = (
            Veterinario.objects.all().order_by("pk")
        )

        self.fields["cita"].queryset = Cita.objects.none()

        if mascota is not None:
            self.fields["cita"].queryset = (
                Cita.objects.filter(
                    mascota=mascota,
                    estado=Cita.Estado.COMPLETADA,
                    atencion_clinica__isnull=True,
                )
                .select_related("veterinario")
                .order_by("-fecha", "-hora_inicio")
            )

        # PETCARE V19.3.2 - Conservar cita propia al editar
        if self.instance.pk and self.instance.cita_id:
            cita_actual = Cita.objects.filter(
                pk=self.instance.cita_id,
                mascota_id=self.instance.ficha.mascota_id,
                estado=Cita.Estado.COMPLETADA,
            )
            self.fields["cita"].queryset = (
                self.fields["cita"].queryset | cita_actual
            ).distinct()

        self.fields["veterinario"].empty_label = "Seleccione un veterinario"

        self.fields["cita"].required = False
        self.fields["cita"].empty_label = "Sin cita asociada"

        self.fields["fecha_atencion"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        if not self.is_bound:
            from django.utils import timezone

            if self.instance.pk:
                self.initial["fecha_atencion"] = (
                    timezone.localtime(
                        self.instance.fecha_atencion
                    ).strftime("%Y-%m-%dT%H:%M")
                )
            else:
                self.initial.setdefault(
                    "fecha_atencion",
                    timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                )

    def clean(self):
        datos = super().clean()

        cita = datos.get("cita")
        veterinario = datos.get("veterinario")

        if cita is not None and veterinario is not None:
            if cita.veterinario_id != veterinario.pk:
                self.add_error(
                    "veterinario",
                    "El veterinario debe coincidir con el de la cita.",
                )

        if cita is not None and self.mascota is not None:
            if cita.mascota_id != self.mascota.pk:
                self.add_error(
                    "cita",
                    "La cita no corresponde a esta mascota.",
                )

        return datos


# PETCARE V20 - FORMULARIOS DE RECETAS

from django.forms import BaseInlineFormSet, inlineformset_factory
from .models import RecetaVeterinaria, MedicamentoRecetado


class RecetaVeterinariaForm(forms.ModelForm):
    class Meta:
        model = RecetaVeterinaria
        fields = (
            "indicaciones_generales",
            "observaciones",
        )
        widgets = {
            "indicaciones_generales": forms.Textarea(
                attrs={"rows": 3}
            ),
            "observaciones": forms.Textarea(
                attrs={"rows": 3}
            ),
        }


class MedicamentoRecetadoForm(forms.ModelForm):
    class Meta:
        model = MedicamentoRecetado
        fields = (
            "nombre",
            "presentacion",
            "dosis",
            "via_administracion",
            "frecuencia",
            "duracion",
            "instrucciones",
        )
        widgets = {
            "instrucciones": forms.Textarea(
                attrs={"rows": 2}
            ),
        }


class BaseMedicamentoRecetadoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        cantidad = 0

        for formulario in self.forms:
            datos = getattr(formulario, "cleaned_data", {})

            if not datos:
                continue

            if datos.get("DELETE"):
                continue

            if datos.get("nombre"):
                cantidad += 1

        if cantidad < 1:
            raise forms.ValidationError(
                "Debe registrar al menos un medicamento."
            )


MedicamentoRecetadoFormSet = inlineformset_factory(
    RecetaVeterinaria,
    MedicamentoRecetado,
    form=MedicamentoRecetadoForm,
    formset=BaseMedicamentoRecetadoFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
