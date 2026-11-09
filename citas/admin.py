from django.contrib import admin







from .models import Cita













# petcare_citas_165r71
class EstadoActivoCitaFilter(admin.SimpleListFilter):
    title = "Estado activo"
    parameter_name = "estado_activo"

    def lookups(self, request, model_admin):
        return (
            ("si", "Programadas / confirmadas"),
        )

    def queryset(self, request, queryset):
        if self.value() == "si":
            return queryset.filter(
                estado__in=["PROGRAMADA", "CONFIRMADA"]
            )
        return queryset

@admin.register(Cita)



class CitaAdmin(admin.ModelAdmin):
    change_form_template = "admin/citas/cita/change_form.html"
    change_list_template = "admin/citas/cita/change_list.html"







    def has_change_permission(self, request, obj=None):



        permiso = super().has_change_permission(request, obj)







        if not permiso:



            return False







        if obj is not None:



            if obj.archivada or obj.estado == Cita.Estado.COMPLETADA:



                return False







        if obj is not None:
            if not self.get_queryset(request).filter(
                pk=obj.pk
            ).exists():
                return False

        return True







    def get_readonly_fields(self, request, obj=None):



        campos = list(super().get_readonly_fields(request, obj))







        if obj is not None:



            campos.append("estado")







        return tuple(dict.fromkeys(campos))







    list_display = (
        'mascota_resumen_pc',
        'veterinario_resumen_pc',
        'fecha_resumen_pc',
        'hora_resumen_pc',
        'duracion_resumen_pc',
        'estado_resumen_pc',
        'ver_cita',
    )







    list_filter = (



        "estado",



        "fecha",



        "veterinario",



    
        EstadoActivoCitaFilter,
)







    search_fields = (



        "mascota__nombre",



        "mascota__tutor__nombre",



        "mascota__tutor__apellido",



        "veterinario__nombre",



        "veterinario__apellido",



        "motivo",



    )







    list_select_related = (



        "mascota",



        "veterinario",



    )







    ordering = (



        "fecha",



        "hora_inicio",



    )







    fieldsets = (



        (



            "Datos de la cita",



            {



                "fields": (



                    "mascota",



                    "veterinario",



                    "fecha",



                    "hora_inicio",



                    "duracion_minutos",



                )



            },



        ),



        (



            "Atencion veterinaria",



            {



                "fields": (



                    "motivo",



                    "estado",



                    "observaciones",



                )



            },



        ),



    )






    def has_delete_permission(self, request, obj=None):


        # PetCare: las citas se conservan; no se eliminan


        # desde Django Admin, ni siquiera por superusuarios.


        return False



    def get_queryset(self, request):

        citas = super().get_queryset(request)

        usuario = request.user



        if not usuario.is_authenticated:

            return citas.none()



        if usuario.is_superuser:

            return citas



        grupos = set(

            usuario.groups.values_list("name", flat=True)

        )



        if grupos.intersection(

            {"Administrador", "Recepcionista"}

        ):

            return citas



        if "Veterinario" in grupos:

            return citas.filter(

                veterinario__usuario=usuario,

                veterinario__activo=True,

            )



        return citas.none()



    def has_view_permission(self, request, obj=None):

        if not super().has_view_permission(request, obj):

            return False



        if obj is None:

            return True



        return self.get_queryset(request).filter(

            pk=obj.pk

        ).exists()

    # petcare_citas_165r68
    def changelist_view(self, request, extra_context=None):
        from django.db.models import Count, Q
        from .models import Cita

        contexto = dict(extra_context or {})

        base = self.get_queryset(request)

        resumen = base.aggregate(
            total=Count("pk"),
            programadas=Count(
                "pk",
                filter=Q(
                    estado__in=[
                        Cita.Estado.PROGRAMADA,
                        Cita.Estado.CONFIRMADA,
                    ]
                ),
            ),
            completadas=Count(
                "pk",
                filter=Q(estado=Cita.Estado.COMPLETADA),
            ),
            canceladas=Count(
                "pk",
                filter=Q(estado=Cita.Estado.CANCELADA),
            ),
        )

        contexto.update({
            "pc_total": resumen["total"],
            "pc_programadas": resumen["programadas"],
            "pc_completadas": resumen["completadas"],
            "pc_canceladas": resumen["canceladas"],
        })

        return super().changelist_view(
            request,
            extra_context=contexto,
        )

    # petcare_citas_165r69

    @admin.display(description="Mascota", ordering="mascota")
    def mascota_resumen_pc(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse(
            "admin:citas_cita_change",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" class="pc-cita-enlace">{}</a>',
            url,
            obj.mascota,
        )

    @admin.display(description="Veterinario", ordering="veterinario")
    def veterinario_resumen_pc(self, obj):
        return str(obj.veterinario)

    @admin.display(description="Fecha", ordering="fecha")
    def fecha_resumen_pc(self, obj):
        return obj.fecha.strftime("%d/%m/%Y")

    @admin.display(description="Hora", ordering="hora_inicio")
    def hora_resumen_pc(self, obj):
        return obj.hora_inicio.strftime("%H:%M")

    @admin.display(description="Duracion", ordering="duracion_minutos")
    def duracion_resumen_pc(self, obj):
        return f"{obj.duracion_minutos} min"

    @admin.display(description="Estado", ordering="estado")
    def estado_resumen_pc(self, obj):
        from django.utils.html import format_html

        colores = {
            "PROGRAMADA": ("#fff0bf", "#805900"),
            "CONFIRMADA": ("#dcecf9", "#104766"),
            "COMPLETADA": ("#d9f4e5", "#12623e"),
            "CANCELADA": ("#fce1e1", "#972d2d"),
        }

        fondo, texto = colores.get(
            obj.estado,
            ("#e9edf1", "#536475"),
        )

        return format_html(
            '<span class="pc-estado" '
            'style="background:{};color:{};">{}</span>',
            fondo,
            texto,
            obj.get_estado_display().upper(),
        )

    @admin.display(description="Acciones")
    def ver_cita(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse(
            "admin:citas_cita_change",
            args=[obj.pk],
        )

        return format_html(
            '<a class="pc-ver-cita" href="{}">'
            'VER CITA</a>',
            url,
        )


# ============================================================
# PETCARE - PASO 165R.37
# Administracion de solicitudes de citas
# Primera etapa: consulta segura
# ============================================================

from .models import SolicitudCita


@admin.register(SolicitudCita)
class SolicitudCitaAdmin(admin.ModelAdmin):
    change_list_template = "admin/citas/solicitudcita/change_list.html"
    change_form_template = "admin/citas/solicitudcita/change_form.html"

    # petcare_solicitud_165r40

    @admin.display(description="Solicitud")
    def ver_solicitud_destacada(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse(
            "admin:citas_solicitudcita_change",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" style="display:inline-block;'
            'background:#104766;color:white;'
            'font-size:14px;font-weight:700;'
            'padding:9px 13px;border-radius:7px;'
            'text-decoration:none;white-space:nowrap;">'
            'VER SOLICITUD {}</a>',
            url,
            obj.pk,
        )

    @admin.display(description="Tutor")
    def tutor_resumido(self, obj):
        return f"{obj.tutor.nombre} {obj.tutor.apellido}"

    @admin.display(description="Mascota")
    def mascota_resumida(self, obj):
        return obj.mascota.nombre

    @admin.display(description="Fecha y hora")
    def fecha_hora_resumida(self, obj):
        from django.utils.formats import date_format
        return (
            f"{date_format(obj.fecha_preferida, 'd/m/Y')} "
            f"- {obj.hora_preferida.strftime('%H:%M')}"
        )

    @admin.display(description="Estado")
    def estado_destacado(self, obj):
        from django.utils.html import format_html

        colores = {
            "PENDIENTE": ("#fff3cd", "#855a00"),
            "APROBADA": ("#dcfce7", "#166534"),
            "RECHAZADA": ("#fee2e2", "#991b1b"),
            "CANCELADA": ("#e5e7eb", "#374151"),
        }

        fondo, texto = colores.get(
            obj.estado, ("#e5e7eb", "#374151")
        )

        return format_html(
            '<span style="background:{};color:{};'
            'padding:7px 11px;border-radius:7px;'
            'font-size:13px;font-weight:700;'
            'white-space:nowrap;">{}</span>',
            fondo,
            texto,
            obj.get_estado_display(),
        )

    list_display = (
        "ver_solicitud_destacada",
        "tutor_resumido",
        "mascota_resumida",
        "fecha_hora_resumida",
        "estado_destacado",
    )

    list_filter = (
        "estado",
        "fecha_preferida",
        "fecha_solicitud",
    )

    search_fields = (
        "tutor__nombre",
        "tutor__apellido",
        "tutor__rut",
        "mascota__nombre",
        "motivo",
    )

    ordering = ("-fecha_solicitud", "-id")

    list_select_related = (
        "tutor",
        "mascota",
    )

    readonly_fields = (
        "tutor",
        "mascota",
        "fecha_preferida",
        "hora_preferida",
        "motivo",
        "estado",
        "cita",
        "observaciones_clinica",
        "fecha_solicitud",
        "acceso_gestion",

    "estado_visual",
    "cita_visual",
    "observaciones_visual",
)

    # petcare_ficha_165r41
    # Ficha organizada sin modificar los datos.

    fieldsets = (
        (
            "01 | Tutor y mascota",
            {
                "fields": (
                    ("tutor", "mascota"),
                ),
                "description": (
                    "Identificacion del tutor responsable "
                    "y de la mascota."
                ),
            },
        ),
        (
            "02 | Fecha y motivo de consulta",
            {
                "fields": (
                    ("fecha_preferida", "hora_preferida"),
                    "motivo",
                ),
                "description": (
                    "Informacion solicitada por el tutor."
                ),
            },
        ),
        (
            "03 | Estado y gestion clinica",
            {
                "fields": (
                    ("estado_visual", "cita_visual"),
                    "observaciones_visual",
                ),
                "description": (
                    "Seguimiento administrativo de la solicitud."
                ),
            },
        ),
        (
            "04 | Registro",
            {
                "fields": (
                    "fecha_solicitud",
                ),
                "classes": ("collapse",),
            },
        ),
    
        (
            "05 | Acciones administrativas",
            {
                "fields": ("acceso_gestion",),
                "description": (
                    "Acceso a la aprobacion o rechazo "
                    "de solicitudes pendientes."
                ),
            },
        ),
)

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        usuario = request.user

        if not usuario.is_authenticated:
            return False

        if usuario.is_superuser:
            return True

        grupos = set(
            usuario.groups.values_list("name", flat=True)
        )

        return bool(
            grupos.intersection(
                {"Administrador", "Recepcionista", "Personal Autorizado"}
            )
        )


    # petcare_gestion_admin_165r50

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()

        propias = [
            path(
                "<int:solicitud_id>/gestionar/",
                self.admin_site.admin_view(
                    self.gestionar_solicitud_view
                ),
                name="citas_solicitudcita_gestionar",
            ),
        ]

        return propias + urls


    # petcare_template_165r53

    # petcare_gestion_165r55
    def gestionar_solicitud_view(self, request, solicitud_id):
        from django.core.exceptions import PermissionDenied, ValidationError
        from django.contrib import messages
        from django.http import HttpResponseNotAllowed
        from django.shortcuts import get_object_or_404, redirect
        from django.template.response import TemplateResponse
        from django.urls import reverse

        from .forms_gestion import (
            AprobarSolicitudCitaForm,
            RechazarSolicitudCitaForm,
        )
        from .gestion_solicitudes import (
            aprobar_solicitud,
            rechazar_solicitud,
        )

        # PETCARE 165R.352.42
        if not self.has_view_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            if not (
                request.user.is_superuser
                or request.user.has_perm(
                    "citas.change_solicitudcita"
                )
            ):
                raise PermissionDenied

        if request.method not in ("GET", "POST"):
            return HttpResponseNotAllowed(["GET", "POST"])

        solicitud = get_object_or_404(
            SolicitudCita.objects.select_related(
                "tutor", "mascota"
            ),
            pk=solicitud_id,
        )

        # PETCARE 165R.352.88 - PRESELECCION VETERINARIO
        veterinario_preferido = solicitud.veterinario_preferido

        datos_iniciales = {}

        if (
            veterinario_preferido is not None
            and veterinario_preferido.activo
        ):
            datos_iniciales["veterinario"] = veterinario_preferido.pk

        formulario_aprobar = AprobarSolicitudCitaForm(
            initial=datos_iniciales
        )
        formulario_rechazar = RechazarSolicitudCitaForm()

        if request.method == "POST":
            if (
                solicitud.estado != SolicitudCita.Estado.PENDIENTE
                or solicitud.cita_id is not None
            ):
                messages.error(
                    request,
                    "La solicitud ya no esta pendiente."
                )
                return redirect(request.path)

            accion = request.POST.get("accion")

            if accion == "aprobar":
                formulario_aprobar = AprobarSolicitudCitaForm(
                    request.POST
                )

                if formulario_aprobar.is_valid():
                    datos = formulario_aprobar.cleaned_data

                    try:
                        cita = aprobar_solicitud(
                            solicitud.pk,
                            datos["veterinario"].pk,
                            datos["duracion_minutos"],
                            datos["observaciones_clinica"],
                        )
                    except (ValidationError, ValueError) as exc:
                        messages.error(request, str(exc))
                    else:
                        messages.success(
                            request,
                            f"Solicitud aprobada. Cita N.? {cita.pk} creada."
                        )
                        return redirect(
                            reverse(
                                "admin:citas_solicitudcita_change",
                                args=[solicitud.pk],
                            )
                        )

            elif accion == "rechazar":
                formulario_rechazar = RechazarSolicitudCitaForm(
                    request.POST
                )

                if formulario_rechazar.is_valid():
                    try:
                        rechazar_solicitud(
                            solicitud.pk,
                            formulario_rechazar.cleaned_data[
                                "observaciones_clinica"
                            ],
                        )
                    except ValidationError as exc:
                        messages.error(request, str(exc))
                    else:
                        messages.success(
                            request,
                            "Solicitud rechazada correctamente."
                        )
                        return redirect(
                            reverse(
                                "admin:citas_solicitudcita_change",
                                args=[solicitud.pk],
                            )
                        )
            else:
                messages.error(request, "Accion no reconocida.")

        contexto = {
            **self.admin_site.each_context(request),
            "title": f"Gestión de solicitud N.º {solicitud.pk}",
            "solicitud": solicitud,
            "formulario_aprobar": formulario_aprobar,
            "formulario_rechazar": formulario_rechazar,
            "volver_url": reverse(
                "admin:citas_solicitudcita_change",
                args=[solicitud.pk],
            ),
        }

        return TemplateResponse(
            request,
            "admin/citas/solicitudcita/gestionar.html",
            contexto,
        )

    # petcare_detalle_165r63
    @admin.display(description="Gestionar solicitud")
    def acceso_gestion(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        if not obj or not obj.pk:
            return "-"

        if (
            obj.estado != SolicitudCita.Estado.PENDIENTE
            or obj.cita_id is not None
        ):
            # PETCARE 165R.352.98 - CORRECCION FORMAT_HTML
            return format_html(
                '<span style="color:#667788;">{}</span>',
                "Solicitud ya gestionada"
            )

        url = reverse(
            "admin:citas_solicitudcita_gestionar",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" style="'
            'display:inline-block;'
            'background:#16764c;'
            'color:#ffffff;'
            'padding:12px 22px;'
            'border-radius:7px;'
            'font-weight:700;'
            'text-decoration:none;'
            'border:1px solid #12623e;'
            '">'
            '&#10004;&#xfe0e; Gestionar solicitud'
            '</a>',
            url,
        )

    # petcare_detalle_165r64
    @admin.display(description="Estado")
    def estado_visual(self, obj):
        from django.utils.html import format_html

        colores = {
            "PENDIENTE": ("#fff0bf", "#805900"),
            "APROBADA": ("#d9f4e5", "#12623e"),
            "RECHAZADA": ("#fce1e1", "#972d2d"),
            "CANCELADA": ("#e9edf1", "#536475"),
        }

        fondo, texto = colores.get(
            obj.estado, ("#e9edf1", "#536475")
        )

        return format_html(
            '<span style="display:inline-block;'
            'background:{};color:{};'
            'padding:7px 13px;border-radius:20px;'
            'font-weight:700;font-size:12px;">{}</span>',
            fondo,
            texto,
            obj.get_estado_display().upper(),
        )

    @admin.display(description="Cita")
    def cita_visual(self, obj):
        from django.utils.html import format_html

        if not obj.cita_id:
            return format_html(
                '<span style="color:#667788;">{}</span>',
                "Sin cita asignada",
            )

        return format_html(
            '<strong>Cita N.&ordm; {}</strong>',
            obj.cita_id,
        )

    @admin.display(description="Observaciones de la cl?nica")
    def observaciones_visual(self, obj):
        from django.utils.html import format_html

        texto = (obj.observaciones_clinica or "").strip()

        if not texto:
            return format_html(
                '<span style="color:#667788;">{}</span>',
                "Sin observaciones",
            )

        return texto

    # petcare_contadores_165r67a
    def changelist_view(self, request, extra_context=None):
        from django.db.models import Count, Q

        resumen = SolicitudCita.objects.aggregate(
            total=Count("pk"),
            pendientes=Count(
                "pk",
                filter=Q(estado="PENDIENTE"),
            ),
            aprobadas=Count(
                "pk",
                filter=Q(estado="APROBADA"),
            ),
            rechazadas_canceladas=Count(
                "pk",
                filter=Q(
                    estado__in=["RECHAZADA", "CANCELADA"]
                ),
            ),
        )

        contexto = dict(extra_context or {})
        contexto.update({
            "pc_total": resumen["total"],
            "pc_pendientes": resumen["pendientes"],
            "pc_aprobadas": resumen["aprobadas"],
            "pc_rechazadas_canceladas":
                resumen["rechazadas_canceladas"],
        })

        return super().changelist_view(
            request,
            extra_context=contexto,
        )
