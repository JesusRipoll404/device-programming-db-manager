"""Acceso a PostgreSQL para el administrador de base de datos de programación
de dispositivos: catálogo de referencias/versiones (`circuits`), histórico de
operaciones de programación (`operations`) y reporte de incidencias
(`problems`).

Esta clase es la capa de datos usada por `main_app.py` (interfaz PyQt5). Es
un proyecto independiente y complementario a la suite de programación/
verificación, pensado para que un administrador dé de alta referencias
nuevas, añada versiones de firmware, revise el histórico de operaciones y
gestione incidencias directamente sobre la base de datos, sin pasar por la
interfaz de producción.

Nota de credenciales: host/puerto/base/usuario/contraseña se leen de
variables de entorno (ver `.env.example`) en lugar de estar embebidas en el
código, tal y como estaban en el proyecto original.
"""

import psycopg2
from datetime import datetime
from os import makedirs, listdir
from os.path import join
from typing import Any, Dict, List, Optional, Tuple, Union
import getpass
import os

# =========================
# Configuración de usuarios permitidos
# =========================
# En el proyecto original esta lista contenía nombres de usuario de Windows
# reales del departamento. Aquí se lee de la variable de entorno
# ALLOWED_USERS (nombres separados por comas), con un valor de ejemplo por
# defecto no funcional, para no publicar identidades reales. Ver
# .env.example.
USERS_OK = [
    u.strip().lower()
    for u in os.environ.get("ALLOWED_USERS", "jdoe,asmith,operator1").split(",")
    if u.strip()
]
username = getpass.getuser().strip().lower()


if username in USERS_OK:
    print(f"Usuario permitido: {username}")
else:
    print(f"Usuario NO permitido: {username}")
    exit()



# =========================
# Constantes / Estados
# =========================
CONNECTED = True
DISCONNECTED = False

# Índices (dependen del orden real en la tabla circuits)
IDX_REFERENCE = 0
IDX_MICRO = 1
IDX_HEX = 2
IDX_PROGRAMMER = 3
IDX_VERSION = 4
IDX_FAMILY = 5
IDX_RESPONSIBLE = 6
IDX_PC = 7





# =========================
# "Esquemas" (nombres de columnas)
# =========================
CIRCUITS_COLUMNS = (
    "reference",
    "microcontroller",
    "hex",
    "programmer",
    "version",
    "family",
    "responsible",
    "pc",
)

REPORTS_COLUMNS = (
    "reference",
    "problem",
    "responsible",
    "time",
)

OPERATIONS_COLUMNS = (
    "operation_date",
    "hora_init",
    "hora_end",
    "duration",
    "reference",
    "hex",
    "programmer",
    "state",
    "hostname",
    "operation_type",
)
CIRCUITS=CIRCUITS_COLUMNS
OPERATIONS=OPERATIONS_COLUMNS
REPORTS=REPORTS_COLUMNS



REPORTS_TABLE: str = "public.problems"
OPERATIONS_TABLE: str = "public.operations"

#"plantillas dict"
CIRCUITS_TEMPLATE = {k: "" for k in CIRCUITS_COLUMNS}
REPORTS_TEMPLATE = {k: "" for k in REPORTS_COLUMNS}
OPERATIONS_TEMPLATE = {k: "" for k in OPERATIONS_COLUMNS}



# =========================
# Parser de versiones con '|'
# =========================
class CircuitsReader:
    def __init__(self, data: dict):
        self.controlador = []
        self.hex = []
        self.version = []
        self.programador = []
        self.familia = []
        self.unwrap(data)

    def unwrap(self, data: dict):
        self.controlador = (data.get("microcontroller") or "").split("|")
        self.hex = (data.get("hex") or "").split("|")
        self.version = (data.get("version") or "").split("|")
        self.programador = (data.get("programmer") or "").split("|")

        fam = data.get("family")
        self.familia = [] if fam is None else fam.split("|")

    def getControlador(self, idx: int):
        return self.controlador[idx]

    def getHex(self, idx: int):
        return self.hex[idx]

    def getProgramador(self, idx: int):
        return self.programador[idx]

    def getFamilia(self):
        return self.familia

    def getVersions(self):
        return self.version


# =========================
# Clase principal de BD
# =========================
class ProgrammingDatabase:
    def __init__(self,user: str,password: str,host: str,database: str,port: str,on_connection_change=None,):
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn_state_callback = on_connection_change
        self.conn = None
        self.error = ""

    # ---------- Conexión ----------
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                port=self.port,
                password=self.password,
            )
            self.error = ""
        except psycopg2.OperationalError as e:
            self.conn = None
            self.error = str(e)

        return self.conn

    def reconnect(self):
        if self.conn is not None and not self.conn.closed:
            return self.conn
        return self.connect()

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def check_db_conn_status(self) -> bool:
        return self.conn is not None and self.conn.closed == 0

    def get_error(self):
        return self.error

    def set_connection_lost_callback(self, callback):
        self.conn_state_callback = callback
    #--------------------------------------------------------------------------------------------------------------------------------
    #TABLA CIRCUIT
    #--------------------------------------------------------------------------------------------------------------------------------
    #METODOS CRUD CIRCUITS BUSCAR , BUSCAR ESPECIAL, AÑADIR REFERENCIA , BORRAR REFERENCIA , ACTUALIZAR REFERENCIA,LEERALLREFERENCIAS,AÑADIR VERSION ,BORRAR VERSION(NOMBRE)
    #--------------------------------------------------------------------------------------------------------------------------------
    def search_reference(self, reference: str, as_tuple: bool = False):
        rows = self._read_("SELECT * FROM circuits WHERE reference = %s;", (reference,))
        if not rows:
            return None

        if as_tuple:
            return rows[0]

        # Devuelve dict (sin mutar globales)
        row = rows[0]
        return {col: row[i] for i, col in enumerate(CIRCUITS_COLUMNS)}
    def search_reference_like(self, pattern: str):
        """
        Busca referencias usando comodines SQL (%).
        Ejemplo: 'REF20%'  o  '%P1'  o  '%2002%'
        """
        query = """
            SELECT *
            FROM circuits
            WHERE UPPER(reference) LIKE %s
            ORDER BY reference;
        """
        return self._read_(query, (pattern.upper(),))


    def search_special(self, special_ref: str):
        rows = self._read_(
            "SELECT * FROM circuits WHERE reference LIKE %(special_ref)s",
            {"special_ref": f"%{special_ref}%"},
        )
        return None if not rows else rows

    def add_reference(self, circuit: tuple):
        self._send_(
            "INSERT INTO circuits VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            circuit,
        )

    def remove_reference(self, reference: str):
        self._send_("DELETE FROM circuits WHERE reference = %s", (reference,))

    def update_reference(self, data: tuple):
        self._send_(
            """
            UPDATE circuits
               SET microcontroller=%s,
                   hex=%s,
                   programmer=%s,
                   version=%s,
                   family=%s,
                   responsible=%s,
                   pc=%s
             WHERE reference=%s
            """,
            (data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[0]),
        )

    def all(self):
        return self._read_("SELECT * FROM circuits;")

    def anadir_version(self, reference: str, version: str, hex_path: str,
                    micro: str = "", programmer: str = "", family: str = "") -> bool:
        # 1) leer
        data = self.search_reference(reference, as_tuple=False)
        if not data:
            self.error = f"No existe la referencia {reference}"
            return False

        # 2) parsear
        r = CircuitsReader(data)

        versions = r.getVersions()
        hexes    = r.hex
        micros   = r.controlador
        progs    = r.programador
        fams     = r.getFamilia()

        # 3) si no me pasas micro/programmer/family, copio el último (lo normal)
        if not micro:
            micro = micros[-1] if micros else ""
        if not programmer:
            programmer = progs[-1] if progs else ""
        if family == "":
            family = fams[-1] if fams else ""

        if version in versions:
            self.error = f"La versión '{version}' ya existe en {reference}"
            return False

        # 4) añadir al final
        versions.append(version)
        hexes.append(hex_path)
        micros.append(micro)
        progs.append(programmer)

        if fams is None or len(fams) == 0:
            fams = [""] * (len(versions) - 1)
        while len(fams) < len(versions) - 1:
            fams.append("")
        fams.append(family)

        # 5) reconstruir strings
        data["version"] = "|".join(versions)
        data["hex"] = "|".join(hexes)
        data["microcontroller"] = "|".join(micros)
        data["programmer"] = "|".join(progs)
        data["family"] = "|".join(fams)

        # 6) update
        tup = tuple(data[k] for k in CIRCUITS_COLUMNS)
        self.update_reference(tup)
        return self.error == ""

    def borrar_version_por_nombre(self, reference: str, version_a_borrar: str) -> bool:
        data = self.search_reference(reference, as_tuple=False)
        if not data:
            self.error = f"No existe la referencia {reference}"
            return False

        r = CircuitsReader(data)

        versions = r.getVersions()
        hexes    = r.hex
        micros   = r.controlador
        progs    = r.programador
        fams     = r.getFamilia()

        if version_a_borrar not in versions:
            self.error = f"La versión '{version_a_borrar}' no existe en {reference}"
            return False

        idx = versions.index(version_a_borrar)

        # Asegurar longitudes (por si la BD está regular)
        n = max(len(versions), len(hexes), len(micros), len(progs))
        while len(versions) < n: versions.append("")
        while len(hexes)    < n: hexes.append("")
        while len(micros)   < n: micros.append("")
        while len(progs)    < n: progs.append("")
        if fams is None or len(fams) == 0:
            fams = [""] * n
        while len(fams) < n: fams.append("")

        # Borrar en TODAS las listas
        for lst in (versions, hexes, micros, progs, fams):
            lst.pop(idx)

        # Reconstruir strings
        data["version"] = "|".join(versions)
        data["hex"] = "|".join(hexes)
        data["microcontroller"] = "|".join(micros)
        data["programmer"] = "|".join(progs)
        data["family"] = "|".join(fams)

        tup = tuple(data[k] for k in CIRCUITS_COLUMNS)
        self.update_reference(tup)
        return self.error == ""



    # ---------------------------------------------------------------------
    # Operations CRUD (table: public.operations)
    # Columns:
    # operation_date(date), hora_init(time), hora_end(time),
    # duration(int), reference(varchar), hex(varchar),
    # programmer(varchar), state(varchar), hostname(varchar)
    # ---------------------------------------------------------------------

    def search_operation(
        self,
        operation_date: str,   # 'YYYY-MM-DD'
        hora_init: str,        # 'HH:MM:SS'
        reference: str,
        hostname: str,
        as_tuple: bool = False
    ) -> Optional[Union[Tuple[Any, ...], Dict[str, Any]]]:
        """
        Search a single operation by composite key:
        (operation_date, hora_init, reference, hostname)
        """
        query = f"""
            SELECT operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type
              FROM {OPERATIONS_TABLE}
             WHERE operation_date = %s
               AND hora_init       = %s
               AND reference       = %s
               AND hostname        = %s;
        """
        rows = self._read_(query, (operation_date, hora_init, reference, hostname))
        if not rows:
            return None

        if as_tuple:
            return rows[0]

        row = rows[0]
        return {col: row[i] for i, col in enumerate(OPERATIONS_COLUMNS)}

    def search_operations_by_reference(self, reference: str, limit: int = 200) -> List[Tuple[Any, ...]]:
        """
        Fetch operations for a given reference (latest first).
        """
        query = f"""
            SELECT operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type
              FROM {OPERATIONS_TABLE}
             WHERE reference = %s
             ORDER BY operation_date DESC, hora_init DESC
             LIMIT %s;
        """
        return self._read_(query, (reference, limit))

    def search_operations_special(self, text: str, limit: int = 200) -> List[Tuple[Any, ...]]:
        """
        Partial match search across several varchar fields.
        """
        query = f"""
            SELECT operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type
              FROM {OPERATIONS_TABLE}
             WHERE reference  ILIKE %(q)s
                OR hex        ILIKE %(q)s
                OR programmer ILIKE %(q)s
                OR state      ILIKE %(q)s
                OR hostname   ILIKE %(q)s
             ORDER BY operation_date DESC, hora_init DESC
             LIMIT %(limit)s;
        """
        return self._read_(query, {"q": f"%{text}%", "limit": limit})

    def add_operation(self, operation_row: Tuple[Any, ...]) -> None:
        """
        Insert an operation row.
        Expected tuple order must match OPERATIONS_COLUMNS exactly.
        """
        if len(operation_row) != len(OPERATIONS_COLUMNS):
            raise ValueError(f"operation_row must have {len(OPERATIONS_COLUMNS)} fields: {OPERATIONS_COLUMNS}")

        query = f"""
            INSERT INTO {OPERATIONS_TABLE}
                (operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s);
        """
        self._send_(query, operation_row)

    def update_operation(
        self,
        operation_date: str,
        hora_init: str,
        reference: str,
        hostname: str,
        hora_end: Optional[str] = None,
        duration: Optional[int] = None,
        hex_path: Optional[str] = None,
        programmer: Optional[str] = None,
        state: Optional[str] = None,
        operation_type: Optional[str] = None,
    ) -> bool:
        sets = []
        values = []

        if hora_end is not None:
            sets.append("hora_end=%s")
            values.append(hora_end)
        if duration is not None:
            sets.append("duration=%s")
            values.append(duration)
        if hex_path is not None:
            sets.append("hex=%s")
            values.append(hex_path)
        if programmer is not None:
            sets.append("programmer=%s")
            values.append(programmer)
        if state is not None:
            sets.append("state=%s")
            values.append(state)
        if operation_type is not None:
            sets.append("operation_type=%s")
            values.append(operation_type)

        if not sets:
            self.error = "update_operation: no hay campos para actualizar."
            return False

        query = f"""
            UPDATE {OPERATIONS_TABLE}
            SET {", ".join(sets)}
            WHERE operation_date = %s
            AND hora_init       = %s
            AND reference       = %s
            AND hostname        = %s;
        """
        values.extend([operation_date, hora_init, reference, hostname])

        affected = self._send_(query, tuple(values))

        if affected == 0:
            if self.operation_exists(operation_date, hora_init, reference, hostname):
                self.error = ("UPDATE no modificó filas: la fila existe, pero seguramente "
                            "los valores eran iguales (o hay triggers que lo pisan).")
            else:
                self.error = ("UPDATE no modificó filas: NO existe esa operación con esa clave "
                            "(operation_date/hora_init/reference/hostname). "
                            "Revisa formato de hora y espacios en hostname.")
            return False

        return True

    def remove_operation(self, operation_date: str, hora_init: str, reference: str, hostname: str) -> None:
        """
        Delete operation identified by (operation_date, hora_init, reference, hostname).
        """
        query = f"""
            DELETE FROM {OPERATIONS_TABLE}
             WHERE operation_date = %s
               AND hora_init       = %s
               AND reference       = %s
               AND hostname        = %s;
        """
        self._send_(query, (operation_date, hora_init, reference, hostname))

    def all_operations(self) -> List[Tuple[Any, ...]]:
        """
        Fetch all operations ordered by date/time DESC.
        """
        query = f"""
            SELECT operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type
              FROM {OPERATIONS_TABLE}
             ORDER BY operation_date DESC, hora_init DESC;
        """
        return self._read_(query)

    def operations_latest(self, limit: int = 200) -> List[Tuple[Any, ...]]:
        """
        Fetch latest operations.
        """
        query = f"""
            SELECT operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname,operation_type
              FROM {OPERATIONS_TABLE}
             ORDER BY operation_date DESC, hora_init DESC
             LIMIT %s;
        """
        return self._read_(query, (limit,))
    def operation_exists(self, operation_date: str, hora_init: str, reference: str, hostname: str) -> bool:
        query = f"""
            SELECT 1
            FROM {OPERATIONS_TABLE}
            WHERE operation_date = %s
            AND hora_init       = %s
            AND reference       = %s
            AND hostname        = %s
            LIMIT 1;
        """
        rows = self._read_(query, (operation_date, hora_init, reference, hostname))
        return bool(rows)
    # ---------------------------------------------------------------------
    # Reports CRUD (table: public.problems)
    # Columns: reference, problem, responsible, time (time is varchar)
    # ---------------------------------------------------------------------
    #BUSCAR REPORT,BUSCAR ESPECIAL REPORT, AÑADIR REPORT,AÑADIR REPORT AHORA,ACTUALIZAR REPORT ,ULTIMO REPORT , TODOS REPORT, BORRAR REPORT
    def search_report(self,reference: str,as_tuple: bool = False) -> Optional[Union[Tuple[Any, ...], Dict[str, Any]]]:
        """
        Search a single report by reference.

        Args:
            reference: Reference key.
            as_tuple: If True returns raw tuple from DB.

        Returns:
            None if not found, otherwise tuple or dict with REPORTS_COLUMNS.
        """
        rows = self._read_(f"SELECT * FROM {REPORTS_TABLE} WHERE reference = %s;", (reference,))
        if not rows:
            return None

        if as_tuple:
            return rows[0]

        row = rows[0]
        return {col: row[i] for i, col in enumerate(REPORTS_COLUMNS)}

    def search_reports_special(self, text: str) -> List[Tuple[Any, ...]]:
        """
        Search reports by partial match on reference or problem.

        Args:
            text: Substring to search.

        Returns:
            List of tuples.
        """
        query = f"""
            SELECT *
              FROM {REPORTS_TABLE}
             WHERE reference ILIKE %(q)s
                OR problem   ILIKE %(q)s
             ORDER BY time DESC
        """
        return self._read_(query, {"q": f"%{text}%"})

    def add_report(self, report: Tuple[str, str, str, str]) -> None:
        """
        Insert a report.

        Expected tuple order:
            (reference, problem, responsible, time_str)

        Note:
            'time' is varchar in DB, so pass a string.
        """
        if len(report) != len(REPORTS_COLUMNS):
            raise ValueError(f"report must have {len(REPORTS_COLUMNS)} fields: {REPORTS_COLUMNS}")

        query = f"""
            INSERT INTO {REPORTS_TABLE} (reference, problem, responsible, time)
            VALUES (%s, %s, %s, %s)
        """
        self._send_(query, report)

    def add_report_now(self, reference: str, problem: str, responsible: str = "") -> None:
        """
        Convenience method to insert report using current timestamp as string.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.add_report((reference, problem, responsible, now_str))

    def update_report(self, data: Tuple[str, str, str, str]) -> None:
        """
        Update a report by reference.

        Expected tuple order:
            (reference, problem, responsible, time_str)
        """
        if len(data) != len(REPORTS_COLUMNS):
            raise ValueError(f"data must have {len(REPORTS_COLUMNS)} fields: {REPORTS_COLUMNS}")

        query = f"""
            UPDATE {REPORTS_TABLE}
               SET problem=%s,
                   responsible=%s,
                   time=%s
             WHERE reference=%s
        """
        self._send_(query, (data[1], data[2], data[3], data[0]))

    def all_reports(self) -> List[Tuple[Any, ...]]:
        """
        Fetch all reports ordered by time (DESC).
        """
        return self._read_(f"SELECT * FROM {REPORTS_TABLE} ORDER BY time DESC;")

    def reports_latest(self, limit: int = 100) -> List[Tuple[Any, ...]]:
        """
        Fetch latest reports with limit.
        """
        return self._read_(f"SELECT * FROM {REPORTS_TABLE} ORDER BY time DESC LIMIT %s;", (limit,))

    def remove_report(self, reference: str) -> None:
        """
        Delete a report by reference.
        """
        self._send_(f"DELETE FROM {REPORTS_TABLE} WHERE reference = %s;", (reference,))

    # Optional: keep backward compatibility with your old names
    def show_all_reports(self):
        return self.all_reports()

    #-----------------------------------------------------------------------------------------------------------------------------
    #BACKUP-----------------------------------------------------------------------------------------------------------------------
    #-----------------------------------------------------------------------------------------------------------------------------
    def create_local_copy(self, output_dir: str) -> bool:
        self.reconnect()
        makedirs(output_dir, exist_ok=True)
        filename = datetime.now().strftime("db_backup (%d-%m-%y %H-%M-%S).csv")
        output_path = join(output_dir, filename)

        try:
            sql_query = "COPY (SELECT * FROM circuits) TO STDOUT WITH CSV HEADER DELIMITER ';'"
            with self.conn.cursor() as cursor:
                with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
                    cursor.copy_expert(sql_query, csv_file)

            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.error = str(e)
            return False

    def get_last_backup(self, bkps_dir: str) -> str:
        files = listdir(bkps_dir)
        files.sort(
            key=lambda f: datetime.strptime(f, "db_backup (%d-%m-%y %H-%M-%S).csv"),
            reverse=True,
        )
        return join(bkps_dir, files[0])
    #-----------------------------------------------------------------------------------------------------------------------------
    #BACKUP-----------------------------------------------------------------------------------------------------------------------
    #-----------------------------------------------------------------------------------------------------------------------------

    # ---------- Helpers privados ----------
    def _send_(self, command: str, values=()):
        try:
            self.reconnect()
            with self.conn.cursor() as cursor:
                cursor.execute(command, values)
                affected = cursor.rowcount  # <- IMPORTANTE
                self.conn.commit()
                self.error = ""
                return affected
        except Exception as e:
            self.error = str(e)
            if self.conn_state_callback is not None:
                msg = "Error ejecutando comando en DB:\n\n" + self.error
                self.conn_state_callback(state_db=DISCONNECTED, msg=msg)
            return 0


    def _read_(self, command: str, values=()):
        try:
            self.reconnect()
            with self.conn.cursor() as cursor:
                cursor.execute(command, values)
                rows = cursor.fetchall()
                self.error = ""
                return rows
        except Exception as e:
            self.error = str(e)
            if self.conn_state_callback is not None:
                msg = "Error leyendo de DB:\n\n" + self.error
                self.conn_state_callback(state_db=DISCONNECTED, msg=msg)
            return []



# =========================
# Ejemplo de uso (main)
# =========================
def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    db = ProgrammingDatabase(
        database=os.environ.get("DB_NAME", "programmer_db"),
        user=os.environ.get("DB_USER", username),
        password=os.environ.get("DB_PASSWORD", "CHANGE_ME"),
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=os.environ.get("DB_PORT", "5432"),
    )
    now = datetime.now()
    operation_date = now.strftime("%Y-%m-%d")

    try:
        if db.connect() is None:
            print("Error al conectar:", db.get_error())
            return

        print("Conexión establecida correctamente.")

        nueva_ref = (
            "REF2002",
            "MCU456",
            "firmware_v1.hex",
            "PICkit4",
            "v1.0",
            "familyY",
            "operator1",
            "PC02",
        )


        op = (
            operation_date,          # operation_date
            "16:18:59",            # hora_init
            "16:19:13",            # hora_end
            14,                    # duratio
            "REF2002-01P1",        # reference
            r"\\FILESERVER\shared\firmware\example_firmware.hex",  # hex (ejemplo, no funcional)
            "PIC",                 # programmer
            "FAILED",              # state
            "WORKSTATION-01",      # hostname (ejemplo)
            "Programming"          # operation_type
        )
        #ok = db.anadir_version(
        #    reference="REF1001",
        #    version="02",
        #    hex_path=r"\\FILESERVER\shared\firmware\REF1001_02.hex",
        #    micro="MCU123")
        #print("OK:", ok, "ERR:", db.get_error())

        problems = (
         "REF2002",
         "Descripción de ejemplo del problema reportado.",
         "operator1"
        )

        db.add_report_now(*problems)  # <-- desempaqueta la tupla en 3 argumentos


        #db.add_operation(op)
        #print(db.search_operations_by_reference("REF2002-01P1", limit=20))
        #print("ULTIMAS:", db.operations_latest(5))
        #db.borrar_version_por_nombre("REF1001", "02")

    except Exception as e:
        print("ERROR:", db.get_error())


        # db.add_reference(nueva_ref)
        # print("Referencia añadida:", nueva_ref[0])
        #ref=db.search_reference("REF-EXAMPLE-01")
        #all_refs = db.all()
        #print("Referencia buscada:", ref)


    finally:
        db.close()


if __name__ == "__main__":
    main()
