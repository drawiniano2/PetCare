from django.contrib import admin

from .models import Tutor


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = (
        "rut",
        "nombre",
        "apellido",
        "telefono",
        "correo",
        "activo",
        "fecha_registro",
    )

    list_display_links = ("rut", "nombre")
    list_filter = ("activo", "fecha_registro")
    search_fields = ("rut", "nombre", "apellido", "correo")
    ordering = ("apellido", "nombre")
    list_per_page = 20
    readonly_fields = ("fecha_registro",)

    fieldsets = (
        ("Identificacion", {
            "fields": ("rut", "nombre", "apellido"),
        }),
        ("Contacto", {
            "fields": ("telefono", "correo", "direccion"),
        }),
        ("Estado y registro", {
            "fields": ("activo", "fecha_registro"),
        }),
    )
