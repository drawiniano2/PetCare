from django.contrib import admin

from .models import Veterinario


@admin.register(Veterinario)
class VeterinarioAdmin(admin.ModelAdmin):

    list_display = (
        "rut",
        "nombre",
        "apellido",
        "especialidad",
        "numero_registro",
        "telefono",
        "activo",
        "usuario",
    )

    list_display_links = ("rut", "nombre")

    list_filter = ("activo", "especialidad")

    search_fields = (
        "rut",
        "nombre",
        "apellido",
        "especialidad",
        "numero_registro",
        "correo",
        "usuario__username",
    )

    ordering = ("apellido", "nombre")
    list_per_page = 20
    readonly_fields = ("fecha_registro",)

    fieldsets = (
        ("Identificacion profesional", {
            "fields": (
                "rut",
                "nombre",
                "apellido",
                "especialidad",
                "numero_registro",
            ),
        }),
        ("Contacto", {
            "fields": (
                "telefono",
                "correo",
            ),
        }),
        ("Cuenta de acceso", {
            "fields": ("usuario",),
            "description": (
                "La vinculacion de cuentas esta reservada "
                "a superusuarios."
            ),
        }),
        ("Estado y registro", {
            "fields": (
                "activo",
                "fecha_registro",
            ),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser:
            campos.append("usuario")

        return tuple(dict.fromkeys(campos))
