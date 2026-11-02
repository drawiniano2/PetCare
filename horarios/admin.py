from django.contrib import admin

from .models import Horario


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):

    list_display = (
        "veterinario",
        "dia_semana",
        "hora_inicio",
        "hora_fin",
        "activo",
    )

    list_display_links = ("veterinario",)

    list_filter = (
        "dia_semana",
        "activo",
        "veterinario",
    )

    search_fields = (
        "veterinario__nombre",
        "veterinario__apellido",
        "veterinario__rut",
    )

    list_select_related = ("veterinario",)
    ordering = ("dia_semana", "hora_inicio")
    list_per_page = 20

    fieldsets = (
        ("Veterinario y dia", {
            "fields": (
                "veterinario",
                "dia_semana",
            ),
        }),
        ("Horario de atencion", {
            "fields": (
                "hora_inicio",
                "hora_fin",
            ),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
    )
