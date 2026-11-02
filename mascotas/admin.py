# PETCARE_PASO_154F_REVISION
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html

from .servicios_solicitudes import (
    aprobar_mascota_nueva,
    rechazar_solicitud,
)

from django.contrib import admin

from .models import Mascota, SolicitudMascota


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "especie",
        "raza",
        "sexo",
        "tutor",
        "microchip",
        "activo",
    )

    list_display_links = ("nombre",)
    list_filter = ("especie", "sexo", "activo")
    search_fields = (
        "nombre",
        "raza",
        "microchip",
        "tutor__nombre",
        "tutor__apellido",
        "tutor__rut",
    )
    list_select_related = ("tutor",)
    ordering = ("nombre",)
    list_per_page = 20
    readonly_fields = ("fecha_registro",)

    fieldsets = (
        ("Identificacion", {
            "fields": (
                "tutor",
                "nombre",
                "especie",
                "raza",
                "sexo",
            ),
        }),
        ("Datos de la mascota", {
            "fields": (
                "fecha_nacimiento",
                "color",
                "microchip",
                "peso",
            ),
        }),
        ("Informacion adicional", {
            "fields": (
                "observaciones",
                "activo",
                "fecha_registro",
            ),
        }),
    )


# PETCARE_PASO_110_ADMIN_SOLICITUDES

@admin.register(SolicitudMascota)
class SolicitudMascotaAdmin(admin.ModelAdmin):
    change_list_template = "admin/mascotas/solicitudmascota/change_list.html"

    list_display = (
        "mascota_tutor_resumen",
        "tipo",
        "estado_visual",
        "fecha_solicitud",
        "accion_revision",
    )

    list_filter = (
        "estado",
        "tipo",
        "fecha_solicitud",
    )

    search_fields = (
        "nombre",
        "microchip",
        "tutor__nombre",
        "tutor__apellido",
        "tutor__rut",
    )

    list_select_related = (
        "tutor",
        "revisado_por",
    )

    ordering = ("-fecha_solicitud",)
    list_per_page = 20

    readonly_fields = (
        "tutor",
        "tipo",
        "nombre",
        "especie",
        "raza",
        "sexo",
        "microchip",
        "informacion_adicional",
        "estado",
        "fecha_solicitud",
        "fecha_revision",
        "revisado_por",
        "observacion_revision",
        "enlace_revision_administrativa",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # PETCARE_PASO_147_DETALLE_SEGURO
        return False

    def has_view_permission(self, request, obj=None):
        usuario = request.user

        return (
            usuario.is_authenticated
            and usuario.is_active
            and usuario.is_staff
            and usuario.has_perm(
                "mascotas.view_solicitudmascota"
            )
        )


    # PETCARE_PASO_156C_PERMISOS
    @admin.display(description="Revision administrativa")
    def enlace_revision_administrativa(self, obj):
        if not obj or not obj.pk:
            return "-"

        url = reverse(
            "admin:mascotas_solicitudmascota_revisar",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" style="display:inline-block;'
            'background:#176b48;color:white;'
            'padding:10px 18px;border-radius:7px;'
            'text-decoration:none;font-weight:600;">'
            'Ir a revision administrativa</a>',
            url,
        )

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))

        permiso = (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
            and request.user.has_perm(
                "mascotas.change_solicitudmascota"
            )
        )

        if not permiso:
            campos = [
                campo for campo in campos
                if campo != "enlace_revision_administrativa"
            ]

        return tuple(campos)


    @admin.display(description="Mascota / Tutor")
    def mascota_tutor_resumen(self, obj):
        return format_html(
            '<strong>{}</strong><br>'
            '<span style="color:#63788a;font-size:12px;">{}</span>',
            obj.nombre,
            obj.tutor,
        )

    @admin.display(description="Estado", ordering="estado")
    def estado_visual(self, obj):
        estilos = {
            "PENDIENTE": ("#fff0bd", "#755000"),
            "APROBADA": ("#d9f3e5", "#176b48"),
            "RECHAZADA": ("#fbe1e3", "#a52b32"),
        }

        fondo, texto = estilos.get(
            obj.estado,
            ("#e9eef3", "#17354d"),
        )

        return format_html(
            '<span style="display:inline-block;'
            'background:{};color:{};'
            'padding:6px 11px;border-radius:20px;'
            'font-weight:700;font-size:12px;">{}</span>',
            fondo,
            texto,
            obj.get_estado_display(),
        )

    # PETCARE_PASO_154F_REVISION
    @admin.display(description="Revision")
    def accion_revision(self, obj):
        url = reverse(
            "admin:mascotas_solicitudmascota_revisar",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" style="display:inline-block;'
            'background:#176b48;color:#fff;'
            'padding:8px 14px;border-radius:7px;'
            'text-decoration:none;font-weight:600;">'
            'Revisar</a>',
            url,
        )

    def get_urls(self):
        rutas = [
            path(
                "<int:solicitud_id>/revisar/",
                self.admin_site.admin_view(self.revisar_solicitud_view),
                name="mascotas_solicitudmascota_revisar",
            ),
        ]
        return rutas + super().get_urls()

    def revisar_solicitud_view(self, request, solicitud_id):
        usuario = request.user

        if not (
            usuario.is_authenticated
            and usuario.is_active
            and usuario.is_staff
            and usuario.has_perm("mascotas.view_solicitudmascota")
        ):
            raise PermissionDenied

        solicitud = get_object_or_404(
            SolicitudMascota.objects.select_related(
                "tutor", "revisado_por"
            ),
            pk=solicitud_id,
        )

        puede_decidir = usuario.has_perm(
            "mascotas.change_solicitudmascota"
        )

        error = None
        motivo = ""

        if request.method == "POST":
            if not puede_decidir:
                raise PermissionDenied

            accion = request.POST.get("accion", "")
            confirmado = request.POST.get("confirmar") == "si"
            motivo = request.POST.get("motivo", "").strip()

            if solicitud.estado != SolicitudMascota.Estado.PENDIENTE:
                error = "La solicitud ya fue revisada."

            elif not confirmado:
                error = "Debe confirmar la decision."

            elif accion not in ("aprobar", "rechazar"):
                error = "Accion no valida."

            elif (
                accion == "aprobar"
                and solicitud.tipo != SolicitudMascota.Tipo.NUEVA
            ):
                error = (
                    "La vinculacion requiere verificar titularidad."
                )

            else:
                try:
                    if accion == "aprobar":
                        aprobar_mascota_nueva(
                            solicitud.pk, usuario, motivo
                        )
                        messages.success(
                            request,
                            "Solicitud aprobada.",
                        )
                    else:
                        rechazar_solicitud(
                            solicitud.pk, usuario, motivo
                        )
                        messages.success(
                            request,
                            "Solicitud rechazada.",
                        )

                    return HttpResponseRedirect(
                        reverse(
                            "admin:mascotas_solicitudmascota_changelist"
                        )
                    )

                except ValidationError as exc:
                    error = "; ".join(exc.messages)

                except IntegrityError:
                    error = "Conflicto de integridad."

        contexto = {
            **self.admin_site.each_context(request),
            "title": "Revision de solicitud",
            "opts": self.model._meta,
            "solicitud": solicitud,
            "puede_decidir": puede_decidir,
            "puede_aprobar": (
                puede_decidir
                and solicitud.estado == SolicitudMascota.Estado.PENDIENTE
                and solicitud.tipo == SolicitudMascota.Tipo.NUEVA
            ),
            "puede_rechazar": (
                puede_decidir
                and solicitud.estado == SolicitudMascota.Estado.PENDIENTE
            ),
            "error_revision": error,
            "motivo": motivo,
        }

        return render(
            request,
            "admin/mascotas/solicitudmascota/revisar.html",
            contexto,
        )

    def has_delete_permission(self, request, obj=None):
        return False
