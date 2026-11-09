
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from citas.models import (
    Cita,
    Servicio,
    PersonalServicio,
    HorarioPersonalServicio,
)
from mascotas.models import Mascota
from tutores.models import Tutor


class CitasEsteticaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tutor = Tutor.objects.create(
            rut="11111111-1",
            nombre="Tutor",
            apellido="Prueba",
            telefono="999999999",
            correo="prueba@example.com",
        )

        cls.mascota = Mascota.objects.create(
            tutor=cls.tutor,
            nombre="Mascota Prueba",
            especie="PERRO",
            sexo="M",
        )

        cls.servicio = Servicio.objects.create(
            nombre="Baño de prueba",
            categoria="ESTETICA",
            duracion_minutos=60,
            activo=True,
        )

        cls.personal = PersonalServicio.objects.create(
            nombre="Personal",
            apellido="Prueba",
            activo=True,
        )

        cls.fecha = date(2026, 12, 7)

        HorarioPersonalServicio.objects.create(
            personal=cls.personal,
            dia_semana=cls.fecha.weekday(),
            hora_inicio=time(9, 0),
            hora_fin=time(17, 0),
            activo=True,
        )

    def crear_cita(self, hora=time(10, 0), **cambios):
        datos = {
            "mascota": self.mascota,
            "servicio": self.servicio,
            "personal_servicio": self.personal,
            "veterinario": None,
            "fecha": self.fecha,
            "hora_inicio": hora,
            "duracion_minutos": 60,
            "motivo": "Prueba automatizada",
        }
        datos.update(cambios)
        return Cita(**datos)

    def test_personal_obligatorio(self):
        cita = self.crear_cita(personal_servicio=None)

        with self.assertRaises(ValidationError):
            cita.full_clean()

    def test_horario_permitido(self):
        cita = self.crear_cita()
        cita.full_clean()
        cita.save()
        self.assertIsNotNone(cita.pk)

    def test_superposicion_rechazada(self):
        primera = self.crear_cita()
        primera.save()

        segunda = self.crear_cita(hora=time(10, 30))

        with self.assertRaises(ValidationError):
            segunda.full_clean()

    def test_cancelacion_libera_horario(self):
        primera = self.crear_cita()
        primera.save()

        primera.estado = Cita.Estado.CANCELADA
        primera.save()

        segunda = self.crear_cita(hora=time(10, 30))
        segunda.full_clean()
