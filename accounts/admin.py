from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import SolicitudAcceso


# PETCARE_REVISION_SOLICITUDES_165R378

class RevisionSolicitudForm(forms.ModelForm):

    class Meta:
        model = SolicitudAcceso
        fields = ("estado", "observaciones")

    def clean(self):
        cleaned = super().clean()

        estado = cleaned.get("estado")
        observaciones = cleaned.get("observaciones", "").strip()

        if estado != SolicitudAcceso.Estado.RECHAZADA:
            raise ValidationError(
                "Por ahora solamente se permite rechazar solicitudes."
            )

        if not observaciones:
            self.add_error(
                "observaciones",
                "Debe indicar el motivo del rechazo."
            )

        return cleaned



# PETCARE_FORMULARIO_APROBACION_165R404

class AprobacionSolicitudForm(forms.Form):
    identidad_verificada = forms.BooleanField(
        label="Confirmo que verifiqué la identidad del solicitante",
        required=True,
    )

    # PETCARE_CONFIRMACION_APROBACION_165R406
    confirmacion = forms.CharField(
        label="Escriba APROBAR para confirmar",
        max_length=7,
        required=True,
    )

    def clean_confirmacion(self):
        valor = self.cleaned_data["confirmacion"].strip()
        if valor != "APROBAR":
            raise forms.ValidationError(
                "Debe escribir exactamente APROBAR."
            )
        return valor

    ficha_veterinaria = forms.ModelChoiceField(
        queryset=None,
        label="Ficha profesional verificada",
        required=False,
        empty_label="Seleccione una ficha veterinaria",
    )

    def __init__(self, *args, solicitud=None, **kwargs):
        from veterinarios.models import Veterinario

        super().__init__(*args, **kwargs)
        self.solicitud = solicitud

        self.fields["ficha_veterinaria"].queryset = (
            Veterinario.objects.none()
        )

        if solicitud is None:
            return

        if solicitud.tipo_cuenta == SolicitudAcceso.TipoCuenta.VETERINARIO:
            self.fields["ficha_veterinaria"].required = True
            self.fields["ficha_veterinaria"].queryset = (
                Veterinario.objects.filter(
                    rut=solicitud.rut,
                    usuario__isnull=True,
                    activo=True,
                )
            )
        else:
            self.fields.pop("ficha_veterinaria")

@admin.register(SolicitudAcceso)
class SolicitudAccesoAdmin(admin.ModelAdmin):

    # PETCARE_RUTA_APROBACION_165R403
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()

        rutas = [
            path(
                "<int:solicitud_id>/aprobar/",
                self.admin_site.admin_view(self.vista_aprobar),
                name="accounts_solicitudacceso_aprobar",
            ),
            path(
                "<int:solicitud_id>/activar/",
                self.admin_site.admin_view(self.vista_activar),
                name="accounts_solicitudacceso_activar",
            ),
        ]

        return rutas + urls

    # PETCARE_ACTIVACION_TEMPORAL_165R440
    def vista_activar(self, request, solicitud_id):
        from django import forms
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.http import HttpResponse
        from django.shortcuts import get_object_or_404, redirect
        from django.middleware.csrf import get_token
        from django.utils.html import escape

        if not request.user.is_active or not request.user.is_superuser:
            raise PermissionDenied

        solicitud = get_object_or_404(
            SolicitudAcceso,
            pk=solicitud_id,
        )

        if (
            solicitud.estado != SolicitudAcceso.Estado.APROBADA
            or not solicitud.usuario_creado_id
        ):
            return HttpResponse(
                "La solicitud no esta aprobada o no tiene cuenta.",
                status=409,
            )

        if solicitud.usuario_creado.is_active:
            return HttpResponse(
                "La cuenta ya esta activa.",
                status=409,
            )

        class FormularioActivacion(forms.Form):
            password = forms.CharField(
                label="Contrasena temporal",
                widget=forms.PasswordInput,
            )
            confirmar = forms.CharField(
                label="Confirmar contrasena",
                widget=forms.PasswordInput,
            )

            def clean(self):
                datos = super().clean()
                password = datos.get("password")
                confirmar = datos.get("confirmar")

                if password and confirmar and password != confirmar:
                    self.add_error(
                        "confirmar",
                        "Las contrasenas no coinciden.",
                    )
                return datos

        formulario = FormularioActivacion(
            request.POST if request.method == "POST" else None
        )

        if request.method == "POST" and formulario.is_valid():
            try:
                validate_password(
                    formulario.cleaned_data["password"],
                    user=solicitud.usuario_creado,
                )
            except DjangoValidationError as error:
                formulario.add_error("password", error)
            else:
                with transaction.atomic():
                    actual = SolicitudAcceso.objects.select_for_update().get(
                        pk=solicitud_id
                    )

                    if (
                        actual.estado != SolicitudAcceso.Estado.APROBADA
                        or not actual.usuario_creado_id
                    ):
                        return HttpResponse(
                            "La solicitud ya no esta disponible.",
                            status=409,
                        )

                    usuario = actual.usuario_creado.__class__.objects.select_for_update().get(
                        pk=actual.usuario_creado_id
                    )

                    if usuario.is_active:
                        return HttpResponse(
                            "La cuenta ya esta activa.",
                            status=409,
                        )

                    usuario.set_password(
                        formulario.cleaned_data["password"]
                    )
                    usuario.is_active = True
                    usuario.save(
                        update_fields=["password", "is_active"]
                    )

                    actual.cambio_password_obligatorio = True
                    actual.save(
                        update_fields=["cambio_password_obligatorio"]
                    )

                messages.success(
                    request,
                    "Cuenta activada. Se exige cambiar la contrasena en el primer ingreso.",
                )

                return redirect(
                    "admin:accounts_solicitudacceso_change",
                    solicitud.pk,
                )

        token = escape(get_token(request))
        campos = formulario.as_p()

        html = f"""
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Activar cuenta PetCare</title>
            <style>
                body {{ font-family:Arial,sans-serif;background:#f3f6fb;
                       color:#24364b;padding:30px; }}
                main {{ max-width:600px;margin:auto;background:white;
                        padding:28px;border-radius:14px; }}
                input {{ padding:10px;width:95%;margin-top:6px; }}
                button {{ background:#142d4e;color:white;border:0;
                          padding:12px 20px;border-radius:8px;cursor:pointer; }}
            </style>
        </head>
        <body>
        <main>
            <h2>Activar cuenta PetCare</h2>
            <p>Usuario: {escape(solicitud.usuario_creado.username)}</p>
            <p>Tipo: {escape(solicitud.get_tipo_cuenta_display())}</p>
            <p>La cuenta se activara con cambio obligatorio de contrasena.</p>
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{token}">
                {campos}
                <button type="submit">Activar cuenta</button>
            </form>
            <p><a href="../">Volver</a></p>
        </main>
        </body>
        </html>
        """

        return HttpResponse(html)

    # PETCARE_PANTALLA_APROBACION_165R405
    def vista_aprobar(self, request, solicitud_id):
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponse
        from django.utils.html import escape
        from django.middleware.csrf import get_token

        if not request.user.is_active or not request.user.is_superuser:
            raise PermissionDenied

        solicitud = get_object_or_404(
            SolicitudAcceso,
            pk=solicitud_id,
        )

        if solicitud.estado != SolicitudAcceso.Estado.PENDIENTE:
            return HttpResponse(
                "Esta solicitud ya fue revisada.",
                status=409,
            )

        formulario = AprobacionSolicitudForm(
            request.POST if request.method == "POST" else None,
            solicitud=solicitud,
        )

        # PETCARE_POST_APROBACION_165R407
        aviso = "Revise los datos antes de confirmar la aprobación."

        if request.method == "POST":
            if formulario.is_valid():
                try:
                    ficha = formulario.cleaned_data.get(
                        "ficha_veterinaria"
                    )

                    usuario = aprobar_solicitud_acceso(
                        solicitud_id=solicitud.pk,
                        administrador=request.user,
                        identidad_verificada=formulario.cleaned_data[
                            "identidad_verificada"
                        ],
                        ficha_veterinaria_id=(
                            ficha.pk if ficha is not None else None
                        ),
                    )

                except ValidationError as error:
                    formulario.add_error(None, error)
                else:
                    messages.success(
                        request,
                        "Solicitud aprobada. "
                        "La cuenta fue creada inactiva y sin contraseña."
                    )
                    from django.shortcuts import redirect
                    return redirect(
                        "admin:accounts_solicitudacceso_change",
                        solicitud.pk,
                    )

        datos = [
            ("Nombre", solicitud.nombre),
            ("Apellido", solicitud.apellido),
            ("RUT", solicitud.rut),
            ("Correo", solicitud.correo),
            ("Usuario solicitado", solicitud.username_solicitado),
            ("Tipo de cuenta", solicitud.get_tipo_cuenta_display()),
        ]

        filas = "".join(
            "<tr><th style='text-align:left;padding:9px'>"
            + escape(etiqueta)
            + "</th><td style='padding:9px'>"
            + escape(str(valor))
            + "</td></tr>"
            for etiqueta, valor in datos
        )

        campos = formulario.as_p()
        token = get_token(request)

        html = """
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Revisión de solicitud - PetCare</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: #f3f6fb;
                    color: #24364b;
                    margin: 0;
                    padding: 30px;
                }
                main {
                    max-width: 760px;
                    margin: auto;
                    background: white;
                    border-radius: 14px;
                    padding: 28px;
                    box-shadow: 0 8px 24px #142d4e15;
                }
                h1 { color: #142d4e; }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                tr { border-bottom: 1px solid #e4eaf2; }
                .aviso {
                    background: #e4f8f5;
                    padding: 14px;
                    border-radius: 8px;
                }
                select, input {
                    padding: 9px;
                    max-width: 100%;
                }
            </style>
        </head>
        <body>
        <main>
            <h1>Revisión de solicitud de acceso</h1>
            <p class="aviso">__AVISO__</p>
            <table>__FILAS__</table>
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="__TOKEN__">
                __CAMPOS__
                <p><button type="submit">
                    Confirmar aprobación
                </button></p>
            </form>
            <p><a href="../">Volver a la solicitud</a></p>
        </main>
        </body>
        </html>
        """

        html = (
            html.replace("__AVISO__", escape(aviso))
            .replace("__FILAS__", filas)
            .replace("__TOKEN__", escape(token))
            .replace("__CAMPOS__", campos)
        )

        return HttpResponse(html)

    form = RevisionSolicitudForm

    # PETCARE_ENLACE_APROBACION_165R409
    list_display = (
        "nombre",
        "apellido",
        "tipo_cuenta",
        "estado",
        "fecha_solicitud",
        "enlace_aprobacion",
    )

    @admin.display(description="Aprobación")
    def enlace_aprobacion(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        if obj.estado == SolicitudAcceso.Estado.APROBADA:
            if obj.usuario_creado_id and not obj.usuario_creado.is_active:
                url = reverse(
                    "admin:accounts_solicitudacceso_activar",
                    args=[obj.pk],
                )
                return format_html(
                    '<a href="{}">Asignar contraseña temporal y activar</a>',
                    url,
                )
            return "Cuenta activa" if obj.usuario_creado_id else "Revisada"

        if obj.estado != SolicitudAcceso.Estado.PENDIENTE:
            return "Revisada"

        url = reverse(
            "admin:accounts_solicitudacceso_aprobar",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}">Revisar aprobación</a>',
            url,
        )

    list_filter = (
        "tipo_cuenta",
        "estado",
        "fecha_solicitud",
    )

    search_fields = (
        "nombre",
        "apellido",
        "correo",
        "username_solicitado",
    )

    ordering = ("-fecha_solicitud",)

    readonly_fields = (
        "nombre",
        "apellido",
        "rut",
        "correo",
        "telefono",
        "username_solicitado",
        "tipo_cuenta",
        "fecha_solicitud",
        "revisado_por",
        "fecha_revision",
        "usuario_creado",
    )

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_active
            and request.user.is_superuser
            and obj is not None
            and obj.estado == SolicitudAcceso.Estado.PENDIENTE
        )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))

        if obj and obj.estado != SolicitudAcceso.Estado.PENDIENTE:
            campos.extend(["estado", "observaciones"])

        return campos

    def save_model(self, request, obj, form, change):
        if not change or not request.user.is_superuser:
            raise ValidationError("Operación no autorizada.")

        with transaction.atomic():
            actual = SolicitudAcceso.objects.select_for_update().get(
                pk=obj.pk
            )

            if actual.estado != SolicitudAcceso.Estado.PENDIENTE:
                raise ValidationError(
                    "Esta solicitud ya fue revisada."
                )

            if obj.estado != SolicitudAcceso.Estado.RECHAZADA:
                raise ValidationError(
                    "Solo se permite rechazar solicitudes."
                )

            actual.estado = SolicitudAcceso.Estado.RECHAZADA
            actual.observaciones = obj.observaciones.strip()
            actual.revisado_por = request.user
            actual.fecha_revision = timezone.now()

            actual.save(update_fields=[
                "estado",
                "observaciones",
                "revisado_por",
                "fecha_revision",
            ])

            obj.revisado_por = actual.revisado_por
            obj.fecha_revision = actual.fecha_revision

        messages.success(
            request,
            "Solicitud rechazada y revisión registrada."
        )


# PETCARE_VALIDACION_APROBACION_165R394

# PETCARE_VALIDACION_REFORZADA_165R396

def validar_aprobacion_solicitud(solicitud):
    from django.contrib.auth import get_user_model
    from veterinarios.models import Veterinario
    from tutores.models import Tutor

    User = get_user_model()
    errores = []

    if solicitud.estado != SolicitudAcceso.Estado.PENDIENTE:
        errores.append("La solicitud ya fue revisada.")

    if solicitud.usuario_creado_id:
        errores.append("La solicitud ya tiene una cuenta asociada.")

    if solicitud.tipo_cuenta not in (
        SolicitudAcceso.TipoCuenta.VETERINARIO,
        SolicitudAcceso.TipoCuenta.PERSONAL,
    ):
        errores.append("Tipo de cuenta no permitido.")

    rut = (solicitud.rut or "").strip()
    correo = (solicitud.correo or "").strip()
    username = (solicitud.username_solicitado or "").strip()

    if not rut or not correo or not username:
        errores.append("Faltan datos obligatorios.")

    if username and User.objects.filter(username__iexact=username).exists():
        errores.append("El nombre de usuario ya existe.")

    if correo and User.objects.filter(email__iexact=correo).exists():
        errores.append("El correo ya pertenece a un usuario.")

    if rut and Tutor.objects.filter(rut=rut).exists():
        errores.append("El RUT ya pertenece a un tutor.")

    otras = SolicitudAcceso.objects.filter(
        estado=SolicitudAcceso.Estado.APROBADA
    )

    if solicitud.pk:
        otras = otras.exclude(pk=solicitud.pk)

    if rut and otras.filter(rut=rut).exists():
        errores.append("El RUT ya tiene una solicitud aprobada.")

    if correo and otras.filter(correo__iexact=correo).exists():
        errores.append("El correo ya tiene una solicitud aprobada.")

    if username and otras.filter(
        username_solicitado__iexact=username
    ).exists():
        errores.append("El usuario solicitado ya fue aprobado.")

    if solicitud.tipo_cuenta == SolicitudAcceso.TipoCuenta.VETERINARIO:
        profesionales = Veterinario.objects.filter(rut=rut)

        if not profesionales.exists():
            errores.append("No existe una ficha veterinaria con este RUT.")
        elif profesionales.filter(usuario__isnull=False).exists():
            errores.append("La ficha veterinaria ya tiene un usuario asociado.")

    return errores


# PETCARE_APROBACION_SEGURA_165R398

def aprobar_solicitud_acceso(solicitud_id, administrador, identidad_verificada=False, ficha_veterinaria_id=None):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from veterinarios.models import Veterinario

    if not administrador.is_active or not administrador.is_superuser:
        raise ValidationError("Solo un superusuario puede aprobar solicitudes.")

    if not identidad_verificada:
        raise ValidationError("Debe verificarse la identidad antes de aprobar.")

    User = get_user_model()

    with transaction.atomic():
        solicitud = SolicitudAcceso.objects.select_for_update().get(
            pk=solicitud_id
        )

        errores = validar_aprobacion_solicitud(solicitud)

        if errores:
            raise ValidationError(errores)

        grupo_nombre = (
            "Veterinario"
            if solicitud.tipo_cuenta == SolicitudAcceso.TipoCuenta.VETERINARIO
            else "Personal Autorizado"
        )

        grupo = Group.objects.get(name=grupo_nombre)

        profesional = None

        # PETCARE_FICHA_EXPLICITA_165R401
        if solicitud.tipo_cuenta == SolicitudAcceso.TipoCuenta.VETERINARIO:
            if ficha_veterinaria_id is None:
                raise ValidationError(
                    "Debe seleccionar y verificar la ficha veterinaria."
                )

            try:
                profesional = Veterinario.objects.select_for_update().get(
                    pk=ficha_veterinaria_id,
                    rut=solicitud.rut,
                    usuario__isnull=True,
                    activo=True,
                )
            except Veterinario.DoesNotExist:
                raise ValidationError(
                    "La ficha veterinaria no coincide o no está disponible."
                )

        elif ficha_veterinaria_id is not None:
            raise ValidationError(
                "Una solicitud de personal no requiere ficha veterinaria."
            )

        usuario = User(
            username=solicitud.username_solicitado.strip(),
            email=solicitud.correo.strip(),
            first_name=solicitud.nombre.strip(),
            last_name=solicitud.apellido.strip(),
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )

        usuario.set_unusable_password()
        usuario.full_clean()
        usuario.save()
        usuario.groups.add(grupo)

        if profesional is not None:
            profesional.usuario = usuario
            profesional.save(update_fields=["usuario"])

        solicitud.estado = SolicitudAcceso.Estado.APROBADA
        solicitud.revisado_por = administrador
        solicitud.fecha_revision = timezone.now()
        solicitud.usuario_creado = usuario
        solicitud.save(update_fields=[
            "estado",
            "revisado_por",
            "fecha_revision",
            "usuario_creado",
        ])

        return usuario
