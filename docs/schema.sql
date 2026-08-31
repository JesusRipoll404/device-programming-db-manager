-- ============================================================
-- Esquema de ejemplo (PostgreSQL) para Device Programming DB Manager
-- ============================================================
-- Este esquema reproduce la estructura funcional de la base de datos
-- original (tablas y tipos de columna), pero NO contiene ningún dato real
-- de producción. Los valores de ejemplo (dummy) sirven únicamente para
-- poder probar la aplicación de extremo a extremo.
--
-- Uso:
--   createdb programmer_db
--   psql -U postgres -d programmer_db -f docs/schema.sql
-- ============================================================

-- ------------------------------------------------------------
-- Tabla circuits: catálogo de referencias de producto y sus
-- versiones de firmware. Cada columna "multivalor" (microcontroller,
-- hex, programmer, version, family) almacena una lista separada por '|',
-- con una posición por cada versión histórica de esa referencia.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS circuits (
    reference       VARCHAR(64)  PRIMARY KEY,
    microcontroller TEXT,   -- ej: "MCU123|MCU123|MCU456"
    hex             TEXT,   -- ej: "fw_v1.hex|fw_v2.hex|fw_v3.hex"
    programmer      TEXT,   -- ej: "PIC|PIC|RENESAS"
    version         TEXT,   -- ej: "v1.0|v1.1|v2.0"
    family          TEXT,   -- ej: "FAMILY_A|FAMILY_A|FAMILY_B"
    responsible     VARCHAR(128),
    pc              VARCHAR(32)  -- "Plan de Control" / plan de verificación asociado
);

-- ------------------------------------------------------------
-- Tabla operations: histórico de operaciones de programación
-- realizadas en planta/laboratorio (una fila por intento).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operations (
    operation_date  DATE         NOT NULL,
    hora_init       TIME         NOT NULL,
    hora_end        TIME,
    duration        INTEGER,               -- segundos
    reference       VARCHAR(64)  NOT NULL,
    hex             TEXT,
    programmer      VARCHAR(64),
    state           VARCHAR(32),           -- OK / FAILED / MANUAL...
    hostname        VARCHAR(128),
    operation_type  VARCHAR(64),
    PRIMARY KEY (operation_date, hora_init, reference, hostname)
);

-- ------------------------------------------------------------
-- Tabla problems: reporte de incidencias asociadas a una referencia.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS problems (
    reference    VARCHAR(64)  NOT NULL,
    problem      TEXT         NOT NULL,
    responsible  VARCHAR(128),
    time         VARCHAR(32)  -- almacenado como texto en el proyecto original
);

-- ============================================================
-- Datos de ejemplo (dummy)
-- ============================================================

INSERT INTO circuits (reference, microcontroller, hex, programmer, version, family, responsible, pc) VALUES
    ('REF1001', 'MCU123', 'fw_ref1001_v1.hex', 'PIC', 'v1.0', 'FAMILY_A', 'operator1', 'PC01'),
    ('REF1002', 'MCU123|MCU123', 'fw_ref1002_v1.hex|fw_ref1002_v2.hex', 'PIC|PIC', 'v1.0|v1.1', 'FAMILY_A|FAMILY_A', 'operator1', 'PC02'),
    ('REF2001', 'MCU456', 'fw_ref2001_v1.hex', 'RENESAS', 'v1.0', 'FAMILY_B', 'operator2', 'PC10'),
    ('REF2002', 'MCU456|MCU789', 'fw_ref2002_v1.hex|fw_ref2002_v2.hex', 'RENESAS|RENESAS', 'v1.0|v2.0', 'FAMILY_B|FAMILY_C', 'operator2', 'PC10'),
    ('REF3001', 'ATMEGA328P', 'fw_ref3001_v1.hex', 'AVR', 'v1.0', 'FAMILY_D', 'operator3', 'PC20')
ON CONFLICT (reference) DO NOTHING;

INSERT INTO operations (operation_date, hora_init, hora_end, duration, reference, hex, programmer, state, hostname, operation_type) VALUES
    (CURRENT_DATE, '09:00:00', '09:00:14', 14, 'REF1001', 'fw_ref1001_v1.hex', 'PIC', 'OK', 'WORKSTATION-01', 'Programming'),
    (CURRENT_DATE, '09:05:00', '09:05:20', 20, 'REF1002', 'fw_ref1002_v2.hex', 'PIC', 'FAILED', 'WORKSTATION-01', 'Programming'),
    (CURRENT_DATE, '10:15:00', '10:15:18', 18, 'REF2001', 'fw_ref2001_v1.hex', 'RENESAS', 'OK', 'WORKSTATION-02', 'Programming')
ON CONFLICT (operation_date, hora_init, reference, hostname) DO NOTHING;

INSERT INTO problems (reference, problem, responsible, time) VALUES
    ('REF2002', 'Ejemplo de incidencia: fallo intermitente de verificación tras programar.', 'operator1', TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')),
    ('REF3001', 'Ejemplo de incidencia: el programador no detecta el dispositivo en el primer intento.', 'operator3', TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'));
