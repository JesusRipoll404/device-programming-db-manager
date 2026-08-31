# Arquitectura

Descripción funcional de los módulos, escrita para este repositorio público
(sin referencias a infraestructura o datos reales de ninguna empresa).

## Contexto

Esta aplicación es una herramienta de administración de base de datos,
complementaria y **separada** de la suite de programación/verificación en
planta (otro repositorio de este mismo autor). Mientras que la suite de
producción solo lee la base de datos para programar dispositivos, este
gestor está pensado para un administrador/responsable de calidad que
necesita:

- Dar de alta referencias nuevas y añadir versiones de firmware.
- Actualizar o borrar versiones existentes de una referencia.
- Consultar y depurar el histórico de operaciones de programación
  (`operations`).
- Gestionar el reporte de incidencias (`problems`).

## Flujo general

1. **Arranque** (`main_app.py`): valida que el usuario del sistema operativo
   esté en la lista de autorizados (`database_manager.py`, a nivel de
   import) y construye la ventana principal con tres vistas (Circuits,
   Reports, Problems) sobre un `QStackedWidget`.
2. **Conexión a BD**: el botón "Connect DB" crea una instancia de
   `ProgrammingDatabase` con las credenciales leídas de variables de entorno
   (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`; ver
   `.env.example`).
3. **Circuits** (tabla `circuits`, ver `docs/schema.sql`): cada referencia
   guarda sus versiones históricas como listas separadas por `|` en las
   columnas `microcontroller`, `hex`, `programmer`, `version` y `family`
   (parseadas por `CircuitsReader`). La UI permite:
   - Buscar por referencia exacta o con comodín `*` (traducido a `LIKE` en
     `search_reference_like`).
   - Crear una referencia nueva desde cero.
   - Copiar una referencia existente como base de una nueva (cambiando el
     campo "Reference" tras seleccionar una fila).
   - Añadir una versión nueva a una referencia existente
     (`anadir_version`), actualizar una versión concreta
     (`update_reference` reconstruyendo las listas `|`) o borrarla
     (`borrar_version_por_nombre`), incluyendo el borrado completo de la
     referencia si era su única versión.
4. **Reports** (tabla `operations`): alta/consulta/borrado del histórico de
   operaciones de programación, con filtro de texto libre
   (`search_operations_special`, `ILIKE` sobre varias columnas).
5. **Problems** (tabla `problems`): alta/consulta/borrado de incidencias
   asociadas a una referencia, con marca de tiempo automática
   (`add_report_now`).

## Capa de datos (`database_manager.py`)

`ProgrammingDatabase` encapsula todo el acceso a PostgreSQL vía `psycopg2`,
con dos helpers privados (`_send_` / `_read_`) que gestionan reconexión,
captura de errores y un callback opcional de "conexión perdida". Expone
CRUD completo para las tres tablas descritas arriba, más utilidades de
respaldo local en CSV (`create_local_copy`, `get_last_backup`).

## Qué se ha quedado fuera de este repositorio (a propósito)

- El esquema real de base de datos y cualquier dato de producción (sustituido
  por `docs/schema.sql`, con datos dummy).
- Credenciales, IP y nombre real del servidor PostgreSQL.
- La lista real de usuarios de Windows autorizados (nombres de empleados).
- El icono de aplicación original.

Ver `redaction-terms.txt` (no versionado, ignorado por `.gitignore`) para el
detalle de qué términos reales se sustituyeron durante la generación de este
repositorio.
