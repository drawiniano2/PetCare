
from .views import mascotas_clinicas_visibles, _perfil_clinico_usuario, atenciones_clinicas_visibles
from django.contrib import admin

from .models import (
    FichaClinica,
    AtencionClinica,
    RecetaVeterinaria,
    MedicamentoRecetado,
)


@admin.register(FichaClinica)
class FichaClinicaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "mascota",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    search_fields = (
        "mascota__nombre",
        "mascota__tutor__nombre",
        "mascota__tutor__apellido",
    )

    list_select_related = ("mascota",)

    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
    )

    fieldsets = (
        ("Paciente", {
            "fields": ("mascota",),
        }),
        ("Antecedentes clinicos", {
            "fields": (
                "antecedentes",
                "alergias",
                "enfermedades_previas",
                "observaciones",
            ),
        }),
        ("Registro", {
            "fields": (
                "fecha_creacion",
                "fecha_actualizacion",
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if (
            not request.user.is_superuser
            and not request.user.groups.filter(
                name__in=["Administrador", "Veterinario"]
            ).exists()
            and request.user.groups.filter(
                name="Recepcionista"
            ).exists()
        ):
            return (
                ("Identificacion del paciente", {
                    "fields": ("mascota",),
                }),
                ("Registro", {
                    "fields": (
                        "fecha_creacion",
                        "fecha_actualizacion",
                    ),
                }),
            )

        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))

        if (
            not request.user.is_superuser
            and not request.user.groups.filter(
                name__in=["Administrador", "Veterinario"]
            ).exists()
            and request.user.groups.filter(
                name="Recepcionista"
            ).exists()
        ):
            campos.append("mascota")

        return tuple(dict.fromkeys(campos))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        perfil = _perfil_clinico_usuario(request.user)

        if perfil == "ADMINISTRADOR":
            return queryset

        if perfil == "VETERINARIO":
            pacientes = mascotas_clinicas_visibles(
                request.user
            )
            return queryset.filter(
                mascota__in=pacientes
            )

        return queryset.none()

    def has_view_permission(self, request, obj=None):
        perfil = _perfil_clinico_usuario(request.user)

        if perfil == "ADMINISTRADOR":
            return super().has_view_permission(
                request, obj
            )

        if perfil == "VETERINARIO":
            if not super().has_view_permission(
                request, obj
            ):
                return False

            if obj is None:
                return True

            return self.get_queryset(request).filter(
                pk=obj.pk
            ).exists()

        return False

    def has_add_permission(self, request):
        if _perfil_clinico_usuario(
            request.user
        ) != "ADMINISTRADOR":
            return False

        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if _perfil_clinico_usuario(
            request.user
        ) != "ADMINISTRADOR":
            return False

        return super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return False




@admin.register(AtencionClinica)
class AtencionClinicaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ficha",
        "veterinario",
        "fecha_atencion",
        "cita",
    )

    list_filter = (
        "fecha_atencion",
        "veterinario",
    )

    search_fields = (
        "ficha__mascota__nombre",
        "ficha__mascota__tutor__nombre",
        "veterinario__nombre",
        "veterinario__apellido",
        "diagnostico",
    )

    list_select_related = (
        "ficha__mascota",
        "veterinario",
        "cita",
    )

    readonly_fields = ("fecha_registro",)

    fieldsets = (
        ("Paciente y profesional", {
            "fields": (
                "ficha",
                "veterinario",
                "cita",
                "fecha_atencion",
            ),
        }),
        ("Evaluacion clinica", {
            "fields": (
                "motivo_consulta",
                "sintomas",
                "diagnostico",
            ),
        }),
        ("Tratamiento y seguimiento", {
            "fields": (
                "tratamiento",
                "indicaciones",
                "observaciones",
            ),
        }),
        ("Registro", {
            "fields": ("fecha_registro",),
        }),
    )

    def get_queryset(self, request):
        return atenciones_clinicas_visibles(
            request.user,
            super().get_queryset(request),
        )

    def has_view_permission(self, request, obj=None):
        perfil = _perfil_clinico_usuario(request.user)

        if perfil not in ("ADMINISTRADOR", "VETERINARIO"):
            return False

        if not super().has_view_permission(request, obj):
            return False

        if obj is None:
            return True

        return self.get_queryset(request).filter(
            pk=obj.pk
        ).exists()

    def has_add_permission(self, request):
        if _perfil_clinico_usuario(
            request.user
        ) != "ADMINISTRADOR":
            return False

        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if _perfil_clinico_usuario(
            request.user
        ) != "ADMINISTRADOR":
            return False

        return super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(
        self, db_field, request, **kwargs
    ):
        if db_field.name == "cita":
            from citas.models import Cita

            kwargs["queryset"] = Cita.objects.filter(
                estado=Cita.Estado.COMPLETADA
            ).order_by("-fecha", "-hora_inicio")

        elif db_field.name == "veterinario":
            from veterinarios.models import Veterinario

            kwargs["queryset"] = Veterinario.objects.filter(
                activo=True
            ).order_by("pk")

        return super().formfield_for_foreignkey(
            db_field, request, **kwargs
        )




# PETCARE V20 - ADMINISTRACION DE RECETAS

class MedicamentoRecetadoInline(admin.StackedInline):
    model = MedicamentoRecetado
    extra = 1

    fields = (
        "nombre",
        "presentacion",
        "dosis",
        "via_administracion",
        "frecuencia",
        "duracion",
        "instrucciones",
    )


@admin.register(RecetaVeterinaria)
class RecetaVeterinariaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "paciente",
        "profesional",
        "fecha_emision",
    )

    list_filter = (
        "fecha_emision",
    )

    search_fields = (
        "atencion__ficha__mascota__nombre",
        "atencion__ficha__mascota__tutor__nombre",
        "atencion__ficha__mascota__tutor__apellido",
        "atencion__veterinario__nombre",
        "atencion__veterinario__apellido",
    )

    list_select_related = (
        "atencion__ficha__mascota",
        "atencion__veterinario",
    )

    readonly_fields = ("fecha_registro",)

    inlines = (MedicamentoRecetadoInline,)

    fieldsets = (
        ("Atencion veterinaria", {
            "fields": (
                "atencion",
                "fecha_emision",
            ),
        }),
        ("Indicaciones de la receta", {
            "fields": (
                "indicaciones_generales",
                "observaciones",
            ),
        }),
        ("Registro", {
            "fields": ("fecha_registro",),
        }),
    )

    @admin.display(description="Paciente")
    def paciente(self, obj):
        return obj.atencion.ficha.mascota

    @admin.display(description="Veterinario")
    def profesional(self, obj):
        return obj.atencion.veterinario

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        perfil = _perfil_clinico_usuario(request.user)

        if perfil == "ADMINISTRADOR":
            return queryset

        if perfil == "VETERINARIO":
            atenciones = atenciones_clinicas_visibles(
                request.user
            )
            return queryset.filter(
                atencion__in=atenciones
            )

        return queryset.none()

    def has_view_permission(self, request, obj=None):
        perfil = _perfil_clinico_usuario(request.user)

        if perfil not in ("ADMINISTRADOR", "VETERINARIO"):
            return False

        if not super().has_view_permission(request, obj):
            return False

        if obj is None:
            return True

        return self.get_queryset(request).filter(
            pk=obj.pk
        ).exists()

    def has_add_permission(self, request):
        if _perfil_clinico_usuario(
            request.user
        ) != "ADMINISTRADOR":
            return False

        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

