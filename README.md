# PetCare

Sistema de gesti?n veterinaria desarrollado con Python y Django.

## Descripci?n

PetCare es una aplicaci?n web orientada a la administraci?n de
informaci?n y procesos de atenci?n veterinaria.

## M?dulos del sistema

- Cuentas y autenticaci?n de usuarios.
- Gesti?n de tutores.
- Registro y administraci?n de mascotas.
- Gesti?n de veterinarios.
- Administraci?n de citas veterinarias.
- Solicitudes de citas y seguimiento de estados.
- Configuraci?n de horarios.
- Historial cl?nico veterinario.
- Panel de administraci?n Django personalizado.

## Tecnolog?as

- Python
- Django
- PostgreSQL
- HTML y CSS
- JavaScript
- Git y GitHub

## Instalaci?n local

1. Clonar el repositorio.
2. Crear un entorno virtual de Python.
3. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crear un archivo `.env` a partir de `.env.example`.
5. Configurar las credenciales de PostgreSQL y una clave
   `SECRET_KEY` segura.
6. Aplicar las migraciones:

   ```bash
   python manage.py migrate
   ```

7. Ejecutar el servidor local:

   ```bash
   python manage.py runserver
   ```

## Configuraci?n y seguridad

El archivo `.env` contiene variables privadas y no debe
incorporarse al repositorio.

Los respaldos, el entorno virtual, los archivos temporales
y las bases de datos locales tambi?n est?n excluidos.

El modo DEBUG debe permanecer desactivado en producci?n.

## Estado del proyecto

Versi?n de desarrollo estable para respaldo y control de versiones.

La comprobaci?n `python manage.py check` se ejecut?
satisfactoriamente el 1 de noviembre de 2026.

El sistema no se presenta como despliegue de producci?n
ni como soluci?n sometida a pruebas integrales.

## Licencia

Pendiente de definir.
