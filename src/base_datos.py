"""
Paso 4: crear la base de datos SQLite y sus tablas desde código.
"""
import sqlite3
from pathlib import Path

RUTA_DB = Path("data/output/sanciones.db")
RUTA_SQL = Path("sql/01_schema.sql")


def conectar(ruta=RUTA_DB):
    """Abre la base (si el archivo no existe, SQLite lo crea)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite NO revisa las relaciones si no se pide en cada conexión
    return conn


def crear_tablas(conn, ruta_sql=RUTA_SQL):
    """Lee el archivo .sql y crea todas las tablas."""
    conn.executescript(Path(ruta_sql).read_text(encoding="utf-8"))
    conn.commit()


def listar_tablas(conn):
    filas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [f[0] for f in filas]


if __name__ == "__main__":
    conn = conectar()
    crear_tablas(conn)
    print(f"Base creada en: {RUTA_DB}")
    for t in listar_tablas(conn):
        columnas = [c[1] for c in conn.execute(f"PRAGMA table_info({t})")]
        print(f"  {t:<20} {len(columnas)} columnas: {', '.join(columnas)}")
    conn.close()