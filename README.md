# Device Programming DB Manager

Herramienta de escritorio (PyQt5) para administrar la base de datos
PostgreSQL que alimenta un flujo de programación en serie de
microcontroladores: alta y versionado de referencias de producto,
consulta/depuración del histórico de operaciones de programación y gestión
de incidencias, todo desde una interfaz gráfica pensada para un
administrador o responsable de calidad (no para el operario de planta).

> Este repositorio es una versión **generalizada** de un proyecto interno
> real, publicada como muestra de portfolio. Todo nombre de empresa, cliente,
> credencial, hostname, ruta de red interna y dato de producción reales han
> sido eliminados o sustituidos por valores de ejemplo.

Es un proyecto independiente y complementario a otro repositorio de este
mismo autor centrado en la programación/verificación en planta; comparten el
mismo esquema conceptual de base de datos (tabla `circuits`) pero
responsabilidades distintas: aquella suite **lee** la base de datos para
programar dispositivos, esta aplicación **administra** esa misma base de
datos (altas, bajas, modificaciones e histórico).

## Características

- Búsqueda de referencia exacta o por patrón con comodín `*` (traducido a
  `LIKE`/`ILIKE` contra PostgreSQL).
- Gestión de referencias de producto con versionado histórico: cada
  referencia guarda una lista de versiones (microcontrolador, HEX,
  programador, familia) codificada como campos separados por `|`, con
  soporte para añadir, actualizar o borrar una versión concreta, o crear una
  referencia nueva copiando los datos de otra existente.
- Vista de histórico de operaciones de programación (tabla `operations`),
  con alta manual, filtro de texto libre y borrado.
- Vista de reporte de incidencias (tabla `problems`), con alta rápida (sin
  diálogo modal), filtro y borrado.
- Validación del usuario del sistema operativo contra una lista de usuarios
  autorizados antes de permitir el arranque de la aplicación.
- Conexión/desconexión manual a la base de datos desde la propia interfaz,
  con indicador visual de estado.

## Arquitectura

Ver [`docs/architecture.md`](docs/architecture.md) para una descripción
módulo a módulo del flujo completo.

| Archivo | Responsabilidad |
|---|---|
| `main_app.py` | Punto de entrada, ventana principal (PyQt5) y las tres vistas (Circuits/Reports/Problems) |
| `database_manager.py` | Acceso a PostgreSQL (CRUD circuits/operations/problems) y validación de usuario |

## Puesta en marcha

### Requisitos

- Python 3.10+
- PostgreSQL accesible (local o remoto).

### Instalación

```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configuración

1. Copia `.env.example` a `.env` y ajusta host/puerto/base/usuario/contraseña
   de PostgreSQL, así como la lista de usuarios autorizados
   (`ALLOWED_USERS`).
2. Crea en tu PostgreSQL las tablas `circuits`, `operations` y `problems`
   con las columnas usadas por la aplicación (ver
   [`docs/architecture.md`](docs/architecture.md) y las consultas SQL en
   `database_manager.py`). Este repositorio no incluye un script de esquema
   ni datos de ejemplo.

### Ejecución

```bash
python main_app.py
```

### Generar ejecutable (PyInstaller)

```bash
build.bat
```

o directamente:

```bash
pyinstaller app.spec
```

El icono original de la aplicación no se incluye en este repositorio; añade
tu propio `app_icon.ico` si quieres generar un ejecutable con icono propio —
el código ya tolera su ausencia.

## Qué se ha quedado fuera de este repositorio (a propósito)

- El esquema real de base de datos y cualquier dato de producción.
- Credenciales, IP y nombre real del servidor PostgreSQL.
- La lista real de usuarios de Windows autorizados (nombres de empleados).
- El icono de aplicación original.

## Licencia

MIT — ver [`LICENSE`](LICENSE).
