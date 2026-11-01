-- Esquema de la base de datos de listas de sanciones (ONU + OFAC)
-- Se puede ejecutar varias veces sin error (IF NOT EXISTS).

-- Una fila por persona / entidad / barco / aeronave
CREATE TABLE IF NOT EXISTS registro (
    id_registro     INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente          TEXT NOT NULL CHECK (fuente IN ('ONU', 'OFAC')),
    id_origen       TEXT NOT NULL,                 -- uid (OFAC) o DATAID (ONU)
    tipo            TEXT NOT NULL CHECK (tipo IN ('INDIVIDUO', 'ENTIDAD', 'BARCO', 'AERONAVE')),
    nombre          TEXT,
    apellido        TEXT,
    nombre_completo TEXT NOT NULL,
    fecha_listado   TEXT,                          -- AAAA-MM-DD (solo ONU la trae)
    observaciones   TEXT,
    UNIQUE (fuente, id_origen)                     -- la clave de origen no se repite
);

-- Varios alias por registro
CREATE TABLE IF NOT EXISTS alias (
    id_alias    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro INTEGER NOT NULL REFERENCES registro (id_registro),
    alias       TEXT NOT NULL,
    tipo_alias  TEXT NOT NULL CHECK (tipo_alias IN ('a.k.a.', 'f.k.a.', 'n.k.a.')),
    calidad     TEXT CHECK (calidad IN ('FUERTE', 'DEBIL'))
);

-- Varias direcciones por registro
CREATE TABLE IF NOT EXISTS direccion (
    id_direccion     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro      INTEGER NOT NULL REFERENCES registro (id_registro),
    pais             TEXT,
    ciudad           TEXT,
    estado_provincia TEXT,
    calle            TEXT,
    codigo_postal    TEXT
);

-- Varias nacionalidades / ciudadanías por registro
CREATE TABLE IF NOT EXISTS nacionalidad (
    id_nacionalidad INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro     INTEGER NOT NULL REFERENCES registro (id_registro),
    pais            TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('nationality', 'citizenship'))
);

-- Varias fechas de nacimiento por registro
CREATE TABLE IF NOT EXISTS fecha_nacimiento (
    id_fecha       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro    INTEGER NOT NULL REFERENCES registro (id_registro),
    fecha          TEXT NOT NULL,                  -- AAAA-MM-DD, AAAA-MM o AAAA
    precision      TEXT NOT NULL CHECK (precision IN ('DIA', 'MES', 'ANIO', 'APROXIMADA', 'RANGO')),
    fecha_original TEXT
);

-- Una fila por cada corrida del proceso
CREATE TABLE IF NOT EXISTS bitacora_ejecucion (
    id_ejecucion INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_inicio TEXT NOT NULL,
    fecha_fin    TEXT,
    fuentes      TEXT NOT NULL,                    -- ej: 'ONU,OFAC'
    estado       TEXT NOT NULL CHECK (estado IN ('EN_CURSO', 'OK', 'ERROR')),
    mensaje      TEXT
);

-- Conteos de cada tabla en cada corrida (para la conciliación entrada = salida + rechazos)
CREATE TABLE IF NOT EXISTS bitacora_detalle (
    id_detalle   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion INTEGER NOT NULL REFERENCES bitacora_ejecucion (id_ejecucion),
    tabla        TEXT NOT NULL,
    entrada      INTEGER NOT NULL,
    salida       INTEGER NOT NULL,
    rechazos     INTEGER NOT NULL
);

-- Filas descartadas y el motivo
CREATE TABLE IF NOT EXISTS rechazo (
    id_rechazo   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion INTEGER NOT NULL REFERENCES bitacora_ejecucion (id_ejecucion),
    tabla        TEXT NOT NULL,
    fuente       TEXT,
    id_origen    TEXT,
    motivo       TEXT NOT NULL
);

-- Índices: aceleran las consultas del Paso 5
CREATE INDEX IF NOT EXISTS ix_alias_registro   ON alias (id_registro);
CREATE INDEX IF NOT EXISTS ix_alias_nombre     ON alias (alias);
CREATE INDEX IF NOT EXISTS ix_direccion_reg    ON direccion (id_registro);
CREATE INDEX IF NOT EXISTS ix_direccion_pais   ON direccion (pais);
CREATE INDEX IF NOT EXISTS ix_nacion_registro  ON nacionalidad (id_registro);
CREATE INDEX IF NOT EXISTS ix_fecha_registro   ON fecha_nacimiento (id_registro);
CREATE INDEX IF NOT EXISTS ix_registro_nombre  ON registro (nombre_completo);

CREATE VIEW IF NOT EXISTS registro_pais AS
SELECT id_registro, pais FROM direccion    WHERE pais IS NOT NULL
UNION
SELECT id_registro, pais FROM nacionalidad WHERE pais IS NOT NULL;