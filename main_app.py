import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel,
    QTableView, QToolBar, QAction,
    QComboBox, QStatusBar, QMessageBox, QStackedWidget,QHeaderView,QPlainTextEdit
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
from database_manager import ProgrammingDatabase, CircuitsReader, username

import socket
from datetime import datetime
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
import ctypes

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)



APP_VERSION = "1.3.0"

CIRCUITS_COLUMNS = [
    "reference",
    "microcontroller",
    "hex",
    "programmer",
    "version",
    "family",
    "responsible",
    "pc",
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.db = None
        self.connected = False

        # Estado de selección / modo
        self.selected_reference = None
        self.selected_version_index = None
        self.in_new_ref_mode = False  # True cuando pulsas "Limpiar campos" para crear referencia nueva

        self.setWindowTitle("Device Programming DB Manager")
        self.resize(1500, 850)
        # El icono original de la aplicación no se incluye en este
        # repositorio (ver README). Si el archivo no existe, QIcon
        # simplemente no muestra icono, sin lanzar excepción.
        self.setWindowIcon(QIcon(resource_path("app_icon.ico")))




        # =========================
        # CENTRAL WIDGET
        # =========================
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # =========================
        # NAVIGATION BAR (global)
        # =========================
        nav_layout = QHBoxLayout()
        self.btn_view_circuits = QPushButton("Circuits")
        self.btn_view_reports = QPushButton("Reports")
        self.btn_view_problems = QPushButton("Problems")

        nav_layout.addWidget(self.btn_view_circuits)
        nav_layout.addWidget(self.btn_view_reports)
        nav_layout.addWidget(self.btn_view_problems)
        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)

        # =========================
        # STACKED PAGES (aquí cambia la GUI)
        # =========================
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # ==========================================================
        # Crear SEARCH BAR (pero NO la añadimos al main_layout)
        # -> se añadirá SOLO a la página Circuits
        # ==========================================================
        search_layout = QHBoxLayout()

        self.conexion_status = QLabel("● Disconnected")
        self.conexion_status.setStyleSheet("color:#ff5252; font-weight: bold;")
        search_layout.addWidget(self.conexion_status)

        self.conexion_btn = QPushButton("Connect DB")
        self.conexion_btn.clicked.connect(self.toggle_connection)
        search_layout.addWidget(self.conexion_btn)

        search_layout.addSpacing(20)
        search_layout.addWidget(QLabel("Reference:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search reference... (use * as wildcard)")
        self.search_input.setFixedHeight(40)
        self.search_input.setFixedWidth(300)

        self.search_btn = QPushButton("Search")
        self.search_btn.setEnabled(False)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        self.search_btn.clicked.connect(self.search_reference)
        self.search_input.returnPressed.connect(self.search_reference)

        search_layout.addStretch()

        # ==========================================================
        # PAGE 0: CIRCUITS
        # ==========================================================
        circuits_page = QWidget()
        circuits_page_layout = QVBoxLayout(circuits_page)

        # 1) Search bar SOLO en Circuits
        circuits_page_layout.addLayout(search_layout)

        # 2) Contenido Circuits: form + tabla (horizontal)
        circuits_content = QWidget()
        circuits_layout = QHBoxLayout(circuits_content)

        # ---------- LEFT PANEL (FORM) ----------
        form_panel = QWidget()
        form_layout = QGridLayout(form_panel)
        form_layout.setVerticalSpacing(10)


        self.inputs = {}

        def add_row(row, label, widget):
            form_layout.addWidget(QLabel(label), row, 0)
            form_layout.addWidget(widget, row, 1)
            self.inputs[label.lower()] = widget

        add_row(0, "Reference", QLineEdit())
        add_row(1, "Microcontroller", QLineEdit())

        programmer = QComboBox()
        programmer.addItems(["", "PIC", "RENESAS", "AVR", "PIC-CUSTOM"])
        add_row(2, "Programmer", programmer)

        # Nombres de familia de ejemplo (catálogo dummy, ver docs/schema.sql).
        # En el proyecto original correspondían a nombres de familia de
        # producto internos.
        family = QComboBox()
        family.addItems(["", "FAMILY_A", "FAMILY_B", "FAMILY_C", "FAMILY_D", "FAMILY_E", "FAMILY_F", "FAMILY_G", "FAMILY_H"])
        add_row(3, "Family", family)

        add_row(4, "Version", QLineEdit())
        add_row(5, "HEX", QLineEdit())
        add_row(6, "Responsible", QLineEdit())
        add_row(7, "PC", QLineEdit())

        # ---------- Buttons ----------
        self.btn_new_ref = QPushButton("➕ Limpiar campos")
        self.btn_new_ref.clicked.connect(self.new_reference)

        self.btn_add = QPushButton("➕ Añadir versión / Crear referencia")
        self.btn_add.clicked.connect(self.add_action)

        self.btn_update = QPushButton("Update versión")
        self.btn_delete = QPushButton("Delete versión")
        self.btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: white;
                    border-radius: 4px;
                    padding: 8px;
                }

                QPushButton:hover {
                    background-color: #F44336;
                }
            """)

        self.btn_update.clicked.connect(self.update_version_action)
        self.btn_delete.clicked.connect(self.delete_version_action)

        for b in (self.btn_add, self.btn_update, self.btn_delete, self.btn_new_ref):
            b.setEnabled(False)

        form_layout.addWidget(self.btn_new_ref, 8, 0, 1, 2)
        form_layout.addWidget(self.btn_add, 9, 0, 1, 2)
        form_layout.addWidget(self.btn_update, 10, 0, 1, 2)
        form_layout.addWidget(self.btn_delete, 11, 0, 1, 2)

        # ---------- RIGHT TABLE ----------
        self.table = QTableView()
        self.model = QStandardItemModel(0, len(CIRCUITS_COLUMNS))
        self.model.setHorizontalHeaderLabels(CIRCUITS_COLUMNS)
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)


        self.table.selectionModel().selectionChanged.connect(self.on_row_selected)
        self.table.doubleClicked.connect(self.copy_reference_to_search)

        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        # Montaje horizontal dentro de Circuits
        circuits_layout.addWidget(form_panel, 1)
        circuits_layout.addWidget(self.table, 4)

        circuits_page_layout.addWidget(circuits_content)

        # PAGE 0 :Añadir Circuits
        self.stack.addWidget(circuits_page)
        # ==========================================================
        # PAGE 1: REPORTS (real)
        # ==========================================================
        self.reports_page = ReportsPage()
        self.stack.addWidget(self.reports_page)

        # ==========================================================
        # PAGE 2: PROBLEMS (real)
        # ==========================================================
        self.problems_page = ProblemsPage()
        self.stack.addWidget(self.problems_page)



        # =========================
        # Conectar navegación
        # =========================
        self.btn_view_circuits.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_view_reports.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_view_problems.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        # Dejar Circuits como vista inicial
        self.stack.setCurrentIndex(0)

        # =========================
        # STATUS BAR
        # =========================
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # =========================
        # STYLE
        # =========================
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #E0E0E0; }
            QLineEdit, QComboBox {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                background-color: #2979FF;
                color: white;
                border-radius: 4px;
                padding: 8px;
            }

            QPushButton:disabled { background-color: #555555; }
            QMessageBox{color:black; }
            QMessageBox QLabel{color:black; }
            QTableView {
                background-color: #1E1E1E;
                color: #E0E0E0;
                gridline-color: #2A2A2A;
                selection-background-color: #2979FF;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                color: white;
                padding: 6px;
            }
            QToolBar { background-color: #1A1A1A; spacing: 8px; }
            QStatusBar { background-color: #1A1A1A; color: #BBBBBB; }
        """)

    # =========================
    # DB connect/disconnect
    # =========================
    def toggle_connection(self):
        if not self.connected:
            self.connect_db()
        else:
            self.disconnect_db()


    def connect_db(self):
        # Credenciales de conexión leídas de variables de entorno (ver
        # .env.example). En el proyecto original estaban embebidas en el
        # código junto con la IP y contraseña reales del servidor.
        self.db = ProgrammingDatabase(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            database=os.environ.get("DB_NAME", "programmer_db"),
            user=os.environ.get("DB_USER", username),
            password=os.environ.get("DB_PASSWORD", "CHANGE_ME"),
            port=os.environ.get("DB_PORT", "5432"),
        )

        conn = self.db.connect()
        if conn is None:
            QMessageBox.critical(self, "DB", self.db.get_error())
            self.db = None
            self.connected = False
            self.search_btn.setEnabled(False)
            self.conexion_status.setText("● Disconnected")
            self.conexion_status.setStyleSheet("color:#ff5252; font-weight: bold;")
            self.update_buttons_state()
            return

        self.connected = True
        self.search_btn.setEnabled(True)
        self.conexion_status.setText("● Connected")
        self.conexion_status.setStyleSheet("color:#00e676; font-weight: bold;")

        if hasattr(self, "reports_page"):
            self.reports_page.set_db(self.db)
        if hasattr(self, "problems_page"):
            self.problems_page.set_db(self.db)
        self.update_buttons_state()

    def disconnect_db(self):
        try:
            if self.db is not None:
                self.db.close()
        except Exception:
            pass

        self.db = None
        self.connected = False
        self.search_btn.setEnabled(False)
        self.conexion_status.setText("● Disconnected")
        self.conexion_status.setStyleSheet("color:#ff5252; font-weight: bold;")

        self.selected_reference = None
        self.selected_version_index = None
        self.in_new_ref_mode = False

        if hasattr(self, "reports_page"):
            self.reports_page.set_db(None)
        if hasattr(self, "problems_page"):
            self.problems_page.set_db(None)

        self.update_buttons_state()

    # =========================
    # SEARCH (supports *)
    # =========================
    def search_reference(self):
        if not self.db or not self.connected:
            QMessageBox.warning(self, "DB", "No estás conectado a la base de datos.")
            return

        raw = self.search_input.text().strip().upper()
        if not raw:
            QMessageBox.information(self, "Buscar", "Introduce una referencia o patrón con *.")
            return

        pattern = raw.replace("*", "%")
        use_like = "%" in pattern

        if use_like:
            rows = self.db.search_reference_like(pattern)
        else:
            one = self.db.search_reference(pattern, as_tuple=True)
            rows = [] if not one else [one]

        self.model.setRowCount(0)
        if not rows:
            self.statusBar().showMessage(f"0 resultados para: {raw}")
            return

        displayed = 0
        for row in rows:
            data = dict(zip(CIRCUITS_COLUMNS, row))
            reader = CircuitsReader(data)

            versions = reader.getVersions()
            micros = reader.controlador
            hexes = reader.hex
            programmers = reader.programador
            families = reader.getFamilia()

            n = len(versions)
            for i in range(n):
                items = []

                item_ref = QStandardItem(data["reference"])
                item_ref.setData(i, Qt.UserRole)
                items.append(item_ref)

                items.append(QStandardItem(micros[i] if i < len(micros) else ""))
                items.append(QStandardItem(hexes[i] if i < len(hexes) else ""))
                items.append(QStandardItem(programmers[i] if i < len(programmers) else ""))
                items.append(QStandardItem(versions[i] if i < len(versions) else ""))
                items.append(QStandardItem(families[i] if i < len(families) else ""))
                items.append(QStandardItem(self.value_by_version(data.get("responsible", ""), i)))
                items.append(QStandardItem(self.value_by_version(data.get("pc", ""), i)))

                self.model.appendRow(items)
                displayed += 1

        self.statusBar().showMessage(f"{displayed} filas (versiones) para: {raw}")

    # =========================
    # Selection / double click
    # =========================
    def on_row_selected(self, selected, deselected):
        sm = self.table.selectionModel()
        if sm is None:
            return

        indexes = sm.selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        ref_item = self.model.item(row, 0)

        self.selected_reference = ref_item.text() if ref_item else None
        self.selected_version_index = ref_item.data(Qt.UserRole) if ref_item else None

        self.in_new_ref_mode = False

        for col_idx, col_name in enumerate(CIRCUITS_COLUMNS):
            item = self.model.item(row, col_idx)
            value = "" if item is None else item.text()
            key = col_name.lower()
            if key in self.inputs:
                widget = self.inputs[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(value)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(value)

        self.update_buttons_state()

    def copy_reference_to_search(self, index):
        row = index.row()
        ref_item = self.model.item(row, 0)
        if ref_item is None:
            return
        ref = ref_item.text().strip()
        if not ref:
            return
        self.search_input.setText(ref)
        self.search_input.setFocus()
        self.search_input.selectAll()

    # =========================
    # Helpers
    # =========================
    def value_by_version(self, value, i):
        if value is None:
            return ""
        s = str(value)
        if "|" not in s:
            return s
        parts = s.split("|")
        if i < len(parts):
            return parts[i]
        return parts[0] if parts else ""

    # =========================
    # Buttons state machine
    # =========================
    def update_buttons_state(self):
        if not self.connected:
            self.btn_new_ref.setEnabled(False)
            self.btn_add.setEnabled(False)
            self.btn_update.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        self.btn_new_ref.setEnabled(True)

        if self.in_new_ref_mode:
            self.btn_add.setEnabled(True)
            self.btn_update.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        if self.selected_reference:
            self.btn_add.setEnabled(True)
            self.btn_update.setEnabled(True)
            self.btn_delete.setEnabled(True)
        else:
            self.btn_add.setEnabled(False)
            self.btn_update.setEnabled(False)
            self.btn_delete.setEnabled(False)

    # =========================
    # New reference mode
    # =========================
    def new_reference(self):
        self.table.clearSelection()

        for w in self.inputs.values():
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)

        self.selected_reference = None
        self.selected_version_index = None
        self.in_new_ref_mode = True

        self.update_buttons_state()
        self.statusBar().showMessage("Nueva referencia: rellena los campos y pulsa ➕ (Crear)")

    # =========================
    # ADD action
    # =========================
    def add_action(self):
        if not self.connected or not self.db:
            return

        data = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                data[key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText().strip()

        if not data.get("reference") or not data.get("version"):
            QMessageBox.warning(self, "Datos incompletos", "Reference y Version son obligatorios")
            return

        ref = data["reference"]

        # ==========================================================
        # 1) NUEVA REFERENCIA DESDE 0
        # ==========================================================
        if self.in_new_ref_mode:
            circuit_tuple = (
                ref,
                data.get("microcontroller", ""),
                data.get("hex", ""),
                data.get("programmer", ""),
                data.get("version", ""),
                data.get("family", ""),
                data.get("responsible", ""),
                data.get("pc", ""),
            )

            self.db.add_reference(circuit_tuple)

            if self.db.get_error():
                QMessageBox.critical(self, "DB", self.db.get_error())
                return

            QMessageBox.information(self, "OK", "Referencia creada correctamente")

            self.in_new_ref_mode = False
            self.selected_reference = ref
            self.selected_version_index = None
            self.search_input.setText(ref)
            self.search_reference()
            self.update_buttons_state()
            return

        # ==========================================================
        # 2) NUEVA REFERENCIA A PARTIR DE OTRA COPIA
        # Si hay una referencia seleccionada pero el campo Reference
        # ha cambiado, entonces no es una versión: es una referencia nueva
        # ==========================================================
        if self.selected_reference and ref != self.selected_reference:
            circuit_tuple = (
                ref,
                data.get("microcontroller", ""),
                data.get("hex", ""),
                data.get("programmer", ""),
                data.get("version", ""),
                data.get("family", ""),
                data.get("responsible", ""),
                data.get("pc", ""),
            )

            self.db.add_reference(circuit_tuple)

            if self.db.get_error():
                QMessageBox.critical(self, "DB", self.db.get_error())
                return

            QMessageBox.information(self, "OK", "Nueva referencia creada correctamente a partir de la copia")

            self.in_new_ref_mode = False
            self.selected_reference = ref
            self.selected_version_index = None
            self.search_input.setText(ref)
            self.search_reference()
            self.update_buttons_state()
            return

        # ==========================================================
        # 3) AÑADIR NUEVA VERSIÓN A REFERENCIA EXISTENTE
        # Si la referencia escrita es la misma que la seleccionada,
        # entonces sí se añade como nueva versión
        # ==========================================================
        ok = self.db.anadir_version(
            ref,
            data.get("version", ""),
            data.get("hex", ""),
            data.get("microcontroller", ""),
            data.get("programmer", ""),
            data.get("family", ""),
        )

        if not ok:
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        QMessageBox.information(self, "OK", "Versión añadida correctamente")
        self.search_input.setText(ref)
        self.search_reference()
        self.update_buttons_state()

    # =========================
    # UPDATE VERSION
    # =========================
    def update_version_action(self):
        if not self.connected or not self.db:
            return

        if not self.selected_reference or self.selected_version_index is None:
            QMessageBox.information(self, "Update", "Selecciona una versión en la tabla para actualizar.")
            return

        ref = self.selected_reference
        i = int(self.selected_version_index)

        new_micro = self.inputs["microcontroller"].text().strip()
        new_hex = self.inputs["hex"].text().strip()
        new_prog = self.inputs["programmer"].currentText().strip()
        new_ver = self.inputs["version"].text().strip()
        new_fam = self.inputs["family"].currentText().strip()
        new_resp = self.inputs["responsible"].text().strip()
        new_pc = self.inputs["pc"].text().strip()

        if not new_ver:
            QMessageBox.warning(self, "Update", "El campo Version no puede estar vacío.")
            return

        original = self.db.search_reference(ref, as_tuple=True)
        if not original:
            QMessageBox.critical(self, "DB", self.db.get_error() or "No se encontró la referencia.")
            return

        original = list(original)

        def replace_at(pipe_string, idx, new_value):
            s = "" if pipe_string is None else str(pipe_string)
            parts = s.split("|") if s else [""]
            while len(parts) <= idx:
                parts.append("")
            parts[idx] = new_value
            return "|".join(parts)

        original[1] = replace_at(original[1], i, new_micro)
        original[2] = replace_at(original[2], i, new_hex)
        original[3] = replace_at(original[3], i, new_prog)
        original[4] = replace_at(original[4], i, new_ver)
        original[5] = replace_at(original[5], i, new_fam)

        original[6] = new_resp
        original[7] = new_pc

        self.db.update_reference(tuple(original))

        if self.db.get_error():
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        QMessageBox.information(self, "OK", f"Versión actualizada correctamente ({ref})")
        self.search_input.setText(ref)
        self.search_reference()

    # =========================
    # DELETE VERSION / DELETE REFERENCE IF LAST VERSION
    # =========================
    def delete_version_action(self):
        if not self.connected or not self.db:
            return

        if not self.selected_reference:
            QMessageBox.information(self, "Delete", "Selecciona una versión en la tabla para borrar.")
            return

        ref = self.selected_reference
        ver = self.inputs["version"].text().strip()

        if not ver:
            QMessageBox.warning(self, "Delete", "El campo Version está vacío (no sé qué versión borrar).")
            return

        # Leer referencia completa
        original = self.db.search_reference(ref, as_tuple=False)
        if not original:
            QMessageBox.critical(self, "DB", self.db.get_error() or "No se encontró la referencia.")
            return

        reader = CircuitsReader(original)
        versions = reader.getVersions()

        # ==========================================================
        # CASO 1: si solo queda una versión, borrar referencia completa
        # ==========================================================
        if len(versions) <= 1:
            msg = (
                f"La referencia '{ref}' solo tiene una versión ('{ver}').\n\n"
                f"Si continúas, se borrará la referencia COMPLETA.\n\n"
                f"¿Deseas continuar?"
            )
            ans = QMessageBox.question(
                self,
                "Confirmar borrado completo",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if ans != QMessageBox.Yes:
                return

            self.db.remove_reference(ref)

            if self.db.get_error():
                QMessageBox.critical(self, "DB", self.db.get_error())
                return

            QMessageBox.information(self, "OK", f"Referencia '{ref}' borrada completamente.")

            # Limpiar formulario
            for w in self.inputs.values():
                if isinstance(w, QLineEdit):
                    w.clear()
                elif isinstance(w, QComboBox):
                    w.setCurrentIndex(0)

            self.selected_reference = None
            self.selected_version_index = None
            self.in_new_ref_mode = False

            self.search_input.clear()
            self.model.setRowCount(0)
            self.update_buttons_state()
            return

        # ==========================================================
        # CASO 2: si hay varias versiones, borrar solo la seleccionada
        # ==========================================================
        msg = f"¿Seguro que quieres borrar SOLO la versión '{ver}' de la referencia '{ref}'?"
        ans = QMessageBox.question(
            self,
            "Confirmar borrado",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        ok = self.db.borrar_version_por_nombre(ref, ver)
        if not ok:
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        QMessageBox.information(self, "OK", f"Versión '{ver}' borrada correctamente.")
        self.search_input.setText(ref)
        self.search_reference()
        self.update_buttons_state()

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # =========================
        # BARRA SUPERIOR (FILTRO + ALTA)
        # =========================
        top = QGridLayout()

        # Filtro
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar operations...")

        # Alta INLINE
        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("Reference")

        self.txt_hex = QLineEdit()
        self.txt_hex.setPlaceholderText("HEX")

        self.txt_programmer = QLineEdit()
        self.txt_programmer.setPlaceholderText("Programmer")

        self.txt_state = QLineEdit()
        self.txt_state.setPlaceholderText("State (OK / FAILED / MANUAL...)")

        self.txt_op_type = QLineEdit()
        self.txt_op_type.setPlaceholderText("Operation type")
        self.txt_op_type.setText("Programming")  # valor por defecto

        self.btn_add = QPushButton("➕ Añadir")
        self.btn_delete = QPushButton("🗑 Borrar")
        self.btn_refresh = QPushButton("Cargar")

        # Layout
        top.addWidget(QLabel("Filtro:"), 0, 0)
        top.addWidget(self.txt_filter, 0, 1, 1, 4)

        top.addWidget(QLabel("Reference:"), 1, 0)
        top.addWidget(self.txt_ref, 1, 1)

        top.addWidget(QLabel("HEX:"), 1, 2)
        top.addWidget(self.txt_hex, 1, 3)

        top.addWidget(QLabel("Programmer:"), 2, 0)
        top.addWidget(self.txt_programmer, 2, 1)

        top.addWidget(QLabel("State:"), 2, 2)
        top.addWidget(self.txt_state, 2, 3)

        top.addWidget(QLabel("Op type:"), 3, 0)
        top.addWidget(self.txt_op_type, 3, 1)

        top.addWidget(self.btn_add, 1, 4)
        top.addWidget(self.btn_delete, 2, 4)
        top.addWidget(self.btn_refresh, 0, 5)

        layout.addLayout(top)

        # =========================
        # TABLA
        # =========================
        self.table = QTableView()
        self.model = QStandardItemModel(0, 10)
        self.model.setHorizontalHeaderLabels([
            "operation_date", "hora_init", "hora_end", "duration",
            "reference", "hex", "programmer", "state",
            "hostname", "operation_type"
        ])
        self.table.setModel(self.model)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table, 1)

        # =========================
        # DB + EVENTOS
        # =========================
        self.db = None

        self.btn_refresh.clicked.connect(self.load_reports)
        self.txt_filter.returnPressed.connect(self.load_reports)
        self.btn_add.clicked.connect(self.add_report_inline)
        self.btn_delete.clicked.connect(self.delete_report_inline)

    def set_db(self, db):
        self.db = db
        self.model.setRowCount(0)

    # =========================
    # LOAD
    # =========================
    def load_reports(self):
        if not self.db:
            return

        text = self.txt_filter.text().strip()
        if text:
            rows = self.db.search_operations_special(text, limit=200)
        else:
            rows = self.db.operations_latest(200)

        self.model.setRowCount(0)
        for r in rows:
            items = [QStandardItem("" if v is None else str(v)) for v in r[:10]]
            self.model.appendRow(items)

    # =========================
    # ADD (USANDO TU op)
    # =========================
    def add_report_inline(self):
        if not self.db:
            QMessageBox.warning(self, "DB", "No conectado a la base de datos")
            return

        reference = self.txt_ref.text().strip()
        hex_path = self.txt_hex.text().strip()
        programmer = self.txt_programmer.text().strip()
        state = self.txt_state.text().strip()
        operation_type = self.txt_op_type.text().strip() or "Programming"

        if not reference:
            QMessageBox.warning(self, "Datos incompletos", "Reference es obligatoria")
            return

        now = datetime.now()
        operation_date = now.strftime("%Y-%m-%d")
        hora_init = now.strftime("%H:%M:%S")
        hora_end = None
        duration = 0
        hostname = socket.gethostname()

        # ✅ EXACTAMENTE COMO YA LO USABAS
        op = (
            operation_date,
            hora_init,
            hora_end,
            duration,
            reference,
            hex_path,
            programmer,
            state,
            hostname,
            operation_type
        )

        self.db.add_operation(op)

        if self.db.get_error():
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        # limpiar + recargar
        self.txt_ref.clear()
        self.txt_hex.clear()
        self.txt_programmer.clear()
        self.txt_state.clear()
        self.load_reports()

    # =========================
    # DELETE
    # =========================
    def delete_report_inline(self):
        if not self.db:
            return

        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Borrar", "Selecciona una operación")
            return

        row = sel[0].row()
        operation_date = self.model.item(row, 0).text()
        hora_init = self.model.item(row, 1).text()
        reference = self.model.item(row, 4).text()
        hostname = self.model.item(row, 8).text()

        msg = (
            "¿Borrar esta operación?\n\n"
            f"{operation_date} {hora_init}\n"
            f"Ref: {reference}\nHost: {hostname}"
        )

        if QMessageBox.question(
            self, "Confirmar", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return

        self.db.remove_operation(operation_date, hora_init, reference, hostname)

        if self.db.get_error():
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        self.load_reports()

class ProblemsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # =========================
        # BARRA SUPERIOR (FILTRO + ALTA)
        # =========================
        top = QGridLayout()

        # Filtro
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar problems (reference/problem)...")

        # Alta directa (SIN diálogo)
        self.txt_new_ref = QLineEdit()
        self.txt_new_ref.setPlaceholderText("Reference nueva")

        # Para problema corto: QLineEdit
        # self.txt_new_problem = QLineEdit()
        # self.txt_new_problem.setPlaceholderText("Descripción del problema...")

        # Para problema largo (recomendado): QPlainTextEdit
        self.txt_new_problem = QPlainTextEdit()
        self.txt_new_problem.setPlaceholderText("Descripción del problema...")
        self.txt_new_problem.setFixedHeight(70)

        self.btn_add = QPushButton("➕ Añadir")
        self.btn_delete = QPushButton("🗑 Borrar")
        self.btn_refresh = QPushButton("Cargar")

        # Layout del bloque superior
        top.addWidget(QLabel("Filtro:"), 0, 0)
        top.addWidget(self.txt_filter, 0, 1, 1, 3)

        top.addWidget(QLabel("Reference:"), 1, 0)
        top.addWidget(self.txt_new_ref, 1, 1)

        top.addWidget(QLabel("Problem:"), 2, 0)
        top.addWidget(self.txt_new_problem, 2, 1, 1, 3)

        top.addWidget(self.btn_add, 1, 2)
        top.addWidget(self.btn_delete, 1, 3)
        top.addWidget(self.btn_refresh, 0, 4)

        layout.addLayout(top)

        # =========================
        # TABLA
        # =========================
        self.table = QTableView()
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(["reference", "problem", "responsible", "time"])
        self.table.setModel(self.model)

        header = self.table.horizontalHeader()

        # Reference
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 140)

        # Problem (ocupa todo el espacio restante)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        # Responsible
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 120)

        # Time
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 180)

        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table, 1)

        # =========================
        # DB + EVENTOS
        # =========================
        self.db = None

        self.btn_refresh.clicked.connect(self.load_problems)
        self.txt_filter.returnPressed.connect(self.load_problems)

        self.btn_add.clicked.connect(self.add_problem_inline)
        self.btn_delete.clicked.connect(self.delete_problem_inline)

    def set_db(self, db):
        self.db = db
        self.model.setRowCount(0)

    # =========================
    # CARGAR (filtro o últimos)
    # =========================
    def load_problems(self):
        if not self.db:
            return

        text = self.txt_filter.text().strip()

        # Usamos TUS métodos reales (sin hasattr si no quieres):
        if text:
            rows = self.db.search_reports_special(text)
        else:
            rows = self.db.reports_latest(200)  # mejor que all_reports si hay muchos

        self.model.setRowCount(0)
        for r in rows:
            items = [QStandardItem("" if v is None else str(v)) for v in r[:4]]
            self.model.appendRow(items)

    # =========================
    # AÑADIR (SIN DIÁLOGO)
    # =========================
    def add_problem_inline(self):
        if not self.db:
            QMessageBox.warning(self, "DB", "No estás conectado a la base de datos.")
            return

        reference = self.txt_new_ref.text().strip()
        problem = self.txt_new_problem.toPlainText().strip()  # QPlainTextEdit
        # si usases QLineEdit: problem = self.txt_new_problem.text().strip()

        if not reference or not problem:
            QMessageBox.warning(self, "Datos incompletos", "Reference y Problem son obligatorios.")
            return

        responsible = socket.gethostname()  # ✅ automático por hostname
        self.db.add_report_now(reference, problem, responsible)

        if self.db.get_error():
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        # Limpiar campos y recargar
        self.txt_new_ref.clear()
        self.txt_new_problem.clear()
        self.load_problems()

    # =========================
    # BORRAR (fila seleccionada)
    # =========================
    def delete_problem_inline(self):
        if not self.db:
            QMessageBox.warning(self, "DB", "No estás conectado a la base de datos.")
            return

        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Borrar", "Selecciona un problema de la tabla.")
            return

        row = sel[0].row()
        reference = self.model.item(row, 0).text().strip()

        if not reference:
            QMessageBox.warning(self, "Borrar", "Reference inválida en la fila seleccionada.")
            return

        msg = f"¿Seguro que quieres borrar el problema asociado a la referencia '{reference}'?"
        if QMessageBox.question(self, "Confirmar borrado", msg,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        # Método real de tu backend
        self.db.remove_report(reference)

        if self.db.get_error():
            QMessageBox.critical(self, "DB", self.db.get_error())
            return

        self.load_problems()


def main():
    # Hace que Windows asocie la ventana con el exe y el icono de la barra
    myappid = "portfolio.deviceprogrammingdbmanager.app.1"
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Aviso AppUserModelID: {e}")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("app_icon.ico")))

    font = app.font()
    font.setPointSize(12)
    app.setFont(font)

    win = MainWindow()
    win.setWindowIcon(QIcon(resource_path("app_icon.ico")))
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
