from django.shortcuts import render

# Create your views here.


# PETCARE HISTORIAL CLINICO V1

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from mascotas.models import Mascota

from .forms import FichaClinicaForm
from .models import FichaClinica



def _perfil_clinico_usuario(usuario):
    """Determina el perfil autorizado para consultas clinicas."""
    if not usuario.is_authenticated or not usuario.is_active:
        return "SIN_ACCESO"

    if usuario.is_superuser:
        return "ADMINISTRADOR"

    grupos = set(
        usuario.groups.values_list("name", flat=True)
    )

    if "Administrador" in grupos:
        return "ADMINISTRADOR"

    if "Veterinario" in grupos:
        return "VETERINARIO"

    if "Recepcionista" in grupos:
        return "RECEPCIONISTA"

    return "SIN_ACCESO"


def mascotas_clinicas_visibles(usuario, queryset=None):
    """Pacientes con acceso clinico autorizado."""
    from mascotas.models import Mascota

    if queryset is None:
        queryset = Mascota.objects.all()

    perfil = _perfil_clinico_usuario(usuario)

    if perfil == "ADMINISTRADOR":
        return queryset

    if perfil == "VETERINARIO":
        return queryset.filter(
            Q(citas__veterinario__usuario=usuario)
            | Q(
                ficha_clinica__atenciones__veterinario__usuario=usuario
            )
        ).distinct()

    return queryset.none()


def atenciones_clinicas_visibles(usuario, queryset=None):
    """Atenciones visibles en un historial compartido."""
    from .models import AtencionClinica

    if queryset is None:
        queryset = AtencionClinica.objects.all()

    perfil = _perfil_clinico_usuario(usuario)

    if perfil == "ADMINISTRADOR":
        return queryset

    if perfil == "VETERINARIO":
        pacientes = mascotas_clinicas_visibles(usuario)
        return queryset.filter(
            ficha__mascota__in=pacientes
        )

    return queryset.none()


def atenciones_clinicas_editables(usuario, queryset=None):
    """Solo las atenciones propias pueden ser modificadas."""
    from .models import AtencionClinica

    if queryset is None:
        queryset = AtencionClinica.objects.all()

    perfil = _perfil_clinico_usuario(usuario)

    if perfil == "ADMINISTRADOR":
        return queryset

    if perfil == "VETERINARIO":
        return queryset.filter(
            veterinario__usuario=usuario,
            veterinario__activo=True,
        )

    return queryset.none()

@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.view_fichaclinica",
    raise_exception=True,
)


# PETCARE 21.5.16.43 - CONTROL CENTRAL DE ACCESO CLINICO



def lista_historiales(request):
    busqueda = request.GET.get("q", "").strip()

    mascotas = mascotas_clinicas_visibles(
        request.user,
        Mascota.objects.select_related(
        "tutor",
        "ficha_clinica",
    ).all(),
    )

    if busqueda:
        mascotas = mascotas.filter(
            Q(nombre__icontains=busqueda)
            | Q(tutor__nombre__icontains=busqueda)
            | Q(tutor__apellido__icontains=busqueda)
        )

    mascotas = mascotas.order_by("nombre", "pk")

    return render(
        request,
        "historial_clinico/lista.html",
        {
            "mascotas": mascotas,
            "busqueda": busqueda,
            "total_mascotas": mascotas.count(),
        },
    )


@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.view_fichaclinica",
    raise_exception=True,
)
def detalle_ficha(request, mascota_id):
    mascota = get_object_or_404(
        mascotas_clinicas_visibles(request.user, Mascota.objects.select_related("tutor")),
        pk=mascota_id,
    )

    ficha = FichaClinica.objects.filter(
        mascota=mascota,
    ).first()

    puede_editar = (_perfil_clinico_usuario(request.user) == "ADMINISTRADOR" and request.user.has_perm(
        "historial_clinico.change_fichaclinica"
    ))

    if ficha is None:
        puede_editar = (_perfil_clinico_usuario(request.user) == "ADMINISTRADOR" and request.user.has_perm(
            "historial_clinico.add_fichaclinica"
        ))

    if request.method == "POST" and not puede_editar:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    if request.method == "POST":
        formulario = FichaClinicaForm(
            request.POST,
            instance=ficha,
        )

        if formulario.is_valid():
            nueva_ficha = formulario.save(commit=False)
            nueva_ficha.mascota = mascota
            nueva_ficha.save()

            messages.success(
                request,
                "Ficha clínica guardada correctamente.",
            )

            return redirect(
                "historial_clinico:detalle",
                mascota_id=mascota.pk,
            )
    else:
        formulario = FichaClinicaForm(instance=ficha)

    atenciones = []

    if ficha is not None:
        atenciones = ficha.atenciones.select_related(
            "veterinario",
            "cita",
        ).all()

    return render(
        request,
        "historial_clinico/detalle.html",
        {
            "mascota": mascota,
            "ficha": ficha,
            "formulario": formulario,
            "atenciones": atenciones,
            "puede_editar": puede_editar,
        },
    )


# PETCARE NUEVA ATENCION CLINICA V1

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .forms import AtencionClinicaForm


@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.add_atencionclinica",
    raise_exception=True,
)
def nueva_atencion(request, mascota_id):
    from veterinarios.models import Veterinario
    from django.core.exceptions import PermissionDenied

    perfil = _perfil_clinico_usuario(request.user)

    if perfil not in ("ADMINISTRADOR", "VETERINARIO"):
        raise PermissionDenied

    # Solo permite pacientes autorizados.
    mascota = get_object_or_404(
        mascotas_clinicas_visibles(
            request.user,
            Mascota.objects.select_related("tutor"),
        ),
        pk=mascota_id,
    )

    ficha = FichaClinica.objects.filter(
        mascota=mascota
    ).first()

    if ficha is None:
        messages.warning(
            request,
            "Primero debe crear la ficha cl?nica de la mascota.",
        )
        return redirect(
            "historial_clinico:detalle",
            mascota_id=mascota.pk,
        )

    veterinario_propio = None

    if perfil == "VETERINARIO":
        veterinario_propio = Veterinario.objects.filter(
            usuario=request.user,
            activo=True,
        ).first()

        if veterinario_propio is None:
            raise PermissionDenied

        veterinarios_permitidos = Veterinario.objects.filter(
            pk=veterinario_propio.pk
        )

    else:
        veterinarios_permitidos = Veterinario.objects.filter(
            activo=True
        )

    if request.method == "POST":
        formulario = AtencionClinicaForm(
            request.POST,
            mascota=mascota,
        )
    else:
        formulario = AtencionClinicaForm(
            mascota=mascota,
        )

    # El queryset restringido impide seleccionar otro veterinario.
    formulario.fields["veterinario"].queryset = (
        veterinarios_permitidos
    )

    if veterinario_propio is not None:
        formulario.initial["veterinario"] = (
            veterinario_propio.pk
        )

    if request.method == "POST" and formulario.is_valid():
        atencion = formulario.save(commit=False)
        atencion.ficha = ficha

        # La identidad del responsable procede de la sesi?n.
        if veterinario_propio is not None:
            atencion.veterinario = veterinario_propio

        try:
            with transaction.atomic():
                atencion.save()

        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for campo, errores in error.message_dict.items():
                    destino = (
                        campo if campo in formulario.fields
                        else None
                    )
                    for mensaje in errores:
                        formulario.add_error(destino, mensaje)
            else:
                for mensaje in error.messages:
                    formulario.add_error(None, mensaje)

        except IntegrityError:
            formulario.add_error(
                "cita",
                "Esta cita ya tiene una atenci?n cl?nica asociada.",
            )

        else:
            messages.success(
                request,
                "Atenci?n veterinaria registrada correctamente.",
            )
            return redirect(
                "historial_clinico:detalle",
                mascota_id=mascota.pk,
            )

    return render(
        request,
        "historial_clinico/nueva_atencion.html",
        {
            "mascota": mascota,
            "ficha": ficha,
            "formulario": formulario,
        },
    )



# PETCARE - DETALLE INDIVIDUAL DE ATENCION
@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.view_atencionclinica",
    raise_exception=True,
)
def detalle_atencion(request, mascota_id, atencion_id):
    from .models import AtencionClinica

    atencion = get_object_or_404(
        atenciones_clinicas_visibles(request.user, AtencionClinica.objects.select_related(
            "ficha__mascota__tutor",
            "veterinario",
            "cita",
        )),
        pk=atencion_id,
        ficha__mascota_id=mascota_id,
    )

    from .models import RecetaVeterinaria

    recetas = (
        RecetaVeterinaria.objects
        .filter(atencion=atencion)
        .prefetch_related('medicamentos')
        .order_by('-fecha_emision', '-id')
    )

    return render(
        request,
        "historial_clinico/detalle_atencion.html",
        {
            "atencion": atencion,
            "mascota": atencion.ficha.mascota,
            "recetas": recetas,
        },
    )

# PETCARE V19 - EDICION DE ATENCIONES CLINICAS
@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.change_atencionclinica",
    raise_exception=True,
)
def editar_atencion(request, mascota_id, atencion_id):
    from .models import AtencionClinica
    from django.db import transaction, IntegrityError
    from django.core.exceptions import ValidationError, PermissionDenied
    from veterinarios.models import Veterinario

    perfil = _perfil_clinico_usuario(request.user)

    if perfil not in ("ADMINISTRADOR", "VETERINARIO"):
        raise PermissionDenied

    atencion = get_object_or_404(
        atenciones_clinicas_editables(
            request.user,
            AtencionClinica.objects.select_related(
                "ficha__mascota__tutor",
                "veterinario",
                "cita",
            ),
        ),
        pk=atencion_id,
        ficha__mascota_id=mascota_id,
    )

    mascota = atencion.ficha.mascota

    if request.method == "POST":
        formulario = AtencionClinicaForm(
            request.POST,
            instance=atencion,
            mascota=mascota,
        )
    else:
        formulario = AtencionClinicaForm(
            instance=atencion,
            mascota=mascota,
        )

    if perfil == "VETERINARIO":
        # El profesional responsable no puede cambiarse.
        formulario.fields["veterinario"].queryset = (
            Veterinario.objects.filter(
                pk=atencion.veterinario_id,
                usuario=request.user,
                activo=True,
            )
        )
        # Tampoco se permite cambiar la cita por una de otro vet.
        formulario.fields["cita"].queryset = (
            formulario.fields["cita"].queryset.filter(
                veterinario_id=atencion.veterinario_id
            )
        )
    else:
        formulario.fields["veterinario"].queryset = (
            Veterinario.objects.filter(activo=True)
        )

    if request.method == "POST" and formulario.is_valid():
        actualizada = formulario.save(commit=False)

        if perfil == "VETERINARIO":
            actualizada.veterinario = atencion.veterinario

        try:
            with transaction.atomic():
                actualizada.save()

        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for campo, errores in error.message_dict.items():
                    destino = (
                        campo if campo in formulario.fields
                        else None
                    )
                    for mensaje in errores:
                        formulario.add_error(destino, mensaje)
            else:
                for mensaje in error.messages:
                    formulario.add_error(None, mensaje)

        except IntegrityError:
            formulario.add_error(
                "cita",
                "Esta cita ya tiene una atencion asociada.",
            )

        else:
            messages.success(
                request,
                "Atencion veterinaria actualizada correctamente.",
            )
            return redirect(
                "historial_clinico:detalle_atencion",
                mascota_id=mascota.pk,
                atencion_id=atencion.pk,
            )

    return render(
        request,
        "historial_clinico/nueva_atencion.html",
        {
            "mascota": mascota,
            "ficha": atencion.ficha,
            "atencion": atencion,
            "formulario": formulario,
            "modo_edicion": True,
        },
    )



# PETCARE V20 - VISTA INICIAL DE RECETAS

@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.add_recetaveterinaria",
    raise_exception=True,
)
def nueva_receta(request, mascota_id, atencion_id):
    from django.shortcuts import get_object_or_404, render, redirect
    from django.db import transaction
    from django.contrib import messages
    from .models import AtencionClinica
    from .forms import (
        RecetaVeterinariaForm,
        MedicamentoRecetadoFormSet,
    )

    atencion = get_object_or_404(
        atenciones_clinicas_editables(request.user, AtencionClinica.objects.select_related(
            "ficha__mascota",
            "veterinario",
        )),
        pk=atencion_id,
        ficha__mascota_id=mascota_id,
    )

    mascota = atencion.ficha.mascota

    if request.method == "POST":
        formulario = RecetaVeterinariaForm(request.POST)
        medicamentos = MedicamentoRecetadoFormSet(
            request.POST,
            prefix="medicamentos",
        )

        if formulario.is_valid() and medicamentos.is_valid():
            with transaction.atomic():
                receta = formulario.save(commit=False)
                receta.atencion = atencion
                receta.save()

                medicamentos.instance = receta
                medicamentos.save()

            messages.success(
                request,
                "Receta veterinaria registrada correctamente.",
            )

            return redirect(
                "historial_clinico:detalle_atencion",
                mascota_id=mascota.pk,
                atencion_id=atencion.pk,
            )

    else:
        formulario = RecetaVeterinariaForm()
        medicamentos = MedicamentoRecetadoFormSet(
            prefix="medicamentos",
        )

    return render(
        request,
        "historial_clinico/nueva_receta.html",
        {
            "mascota": mascota,
            "atencion": atencion,
            "formulario": formulario,
            "medicamentos": medicamentos,
        },
    )


# PETCARE V20 - DETALLE INDIVIDUAL DE RECETA VETERINARIA

@login_required(login_url="/admin/login/")
@permission_required(
    "historial_clinico.view_recetaveterinaria",
    raise_exception=True,
)
def detalle_receta(request, mascota_id, atencion_id, receta_id):
    from .models import RecetaVeterinaria

    receta = get_object_or_404(
        RecetaVeterinaria.objects
        .select_related(
            "atencion__ficha__mascota__tutor",
            "atencion__veterinario",
        )
        .prefetch_related("medicamentos").filter(atencion__in=atenciones_clinicas_visibles(request.user)),
        pk=receta_id,
        atencion_id=atencion_id,
        atencion__ficha__mascota_id=mascota_id,
    )

    atencion = receta.atencion
    mascota = atencion.ficha.mascota

    return render(
        request,
        "historial_clinico/detalle_receta.html",
        {
            "receta": receta,
            "atencion": atencion,
            "mascota": mascota,
        },
    )
