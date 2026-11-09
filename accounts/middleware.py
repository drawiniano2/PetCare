# PETCARE_MIDDLEWARE_PASSWORD_165R432
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.conf import settings

from accounts.models import SolicitudAcceso


class CambioPasswordObligatorioMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user

        if usuario.is_authenticated:
            pendiente = SolicitudAcceso.objects.filter(
                usuario_creado=usuario,
                estado=SolicitudAcceso.Estado.APROBADA,
                cambio_password_obligatorio=True,
            ).exists()

            if pendiente:
                coincidencia = getattr(
                    request, "resolver_match", None
                )

                if coincidencia is None:
                    ruta = request.path_info
                    prefijo = settings.FORCE_SCRIPT_NAME or ""

                    if prefijo and (
                        ruta == prefijo
                        or ruta.startswith(prefijo + "/")
                    ):
                        ruta = ruta[len(prefijo):] or "/"

                    try:
                        coincidencia = resolve(ruta)
                    except Resolver404:
                        coincidencia = None

                nombre_ruta = (
                    coincidencia.url_name
                    if coincidencia is not None
                    else None
                )

                permitidas = {
                    "cambiar_password_obligatorio",
                    "petcare_logout",
                }

                if nombre_ruta not in permitidas:
                    return redirect(
                        "cambiar_password_obligatorio"
                    )

        return self.get_response(request)
