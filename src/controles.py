"""
Controles de calidad sobre la base ya cargada (sección 4.4).
Cada control cuenta las filas que VIOLAN la regla: el resultado esperado siempre es 0.
Uso:  python src/controles.py
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from base_datos import conectar, RUTA_DB

SALIDA = Path("docs/resultados_controles.txt")

# (nombre del control, consulta que devuelve el número de filas que lo violan)
CONTROLES_SQL = [
    # --- Unicidad de claves principales ---
    ("Unicidad: (fuente, id_origen) repetidos en registro",
     "SELECT COUNT(*) FROM (SELECT 1 FROM registro GROUP BY fuente, id_origen HAVING COUNT(*) > 1)"),
    ("Unicidad: registros sin id_origen",
     "SELECT COUNT(*) FROM registro WHERE id_origen IS NULL OR TRIM(id_origen) = ''"),

    # --- Integridad referencial: cada hijo debe tener su registro ---
    ("Integridad: alias sin registro",
     "SELECT COUNT(*) FROM alias a LEFT JOIN registro r ON r.id_registro = a.id_registro WHERE r.id_registro IS NULL"),
    ("Integridad: direcciones sin registro",
     "SELECT COUNT(*) FROM direccion d LEFT JOIN registro r ON r.id_registro = d.id_registro WHERE r.id_registro IS NULL"),
    ("Integridad: nacionalidades sin registro",
     "SELECT COUNT(*) FROM nacionalidad n LEFT JOIN registro r ON r.id_registro = n.id_registro WHERE r.id_registro IS NULL"),
    ("Integridad: fechas de nacimiento sin registro",
     "SELECT COUNT(*) FROM fecha_nacimiento f LEFT JOIN registro r ON r.id_registro = f.id_registro WHERE r.id_registro IS NULL"),

    # --- Fechas válidas ---
    ("Fechas: fecha_nacimiento con formato o calendario inválido",
     """SELECT COUNT(*) FROM fecha_nacimiento WHERE NOT (
            (LENGTH(fecha) = 10 AND DATE(fecha) = fecha)
         OR (LENGTH(fecha) = 7  AND DATE(fecha || '-01') = fecha || '-01')
         OR (LENGTH(fecha) = 4  AND fecha GLOB '[0-9][0-9][0-9][0-9]'))"""),
    ("Fechas: nacimiento fuera del rango 1850 - año actual",
     "SELECT COUNT(*) FROM fecha_nacimiento WHERE CAST(SUBSTR(fecha, 1, 4) AS INTEGER) NOT BETWEEN 1850 AND CAST(STRFTIME('%Y', 'now') AS INTEGER)"),
    ("Fechas: fecha_listado inválida o futura",
     "SELECT COUNT(*) FROM registro WHERE fecha_listado IS NOT NULL AND (DATE(fecha_listado) IS NOT fecha_listado OR fecha_listado > DATE('now'))"),

    # --- Normalización de nombres ---
    ("Nombres: nombre_completo vacío, con espacios al borde o dobles",
     "SELECT COUNT(*) FROM registro WHERE nombre_completo = '' OR nombre_completo <> TRIM(nombre_completo) OR nombre_completo LIKE '%  %'"),
    ("Nombres: alias vacío, con espacios al borde o dobles",
     "SELECT COUNT(*) FROM alias WHERE alias = '' OR alias <> TRIM(alias) OR alias LIKE '%  %'"),
]


def control_mayusculas(conn):
    """Los nombres deben estar en MAYÚSCULAS (se revisa en Python porque UPPER de SQLite no cubre acentos)."""
    nombres = pd.read_sql("SELECT nombre_completo FROM registro", conn)["nombre_completo"]
    return int((nombres != nombres.str.upper()).sum())


def control_conciliacion(conn):
    """En la última ejecución OK: entrada = salida + rechazos y salida = filas reales en la base."""
    ultima = conn.execute("SELECT MAX(id_ejecucion) FROM bitacora_ejecucion WHERE estado = 'OK'").fetchone()[0]
    if ultima is None:
        return 1                                    # no hay ninguna ejecución exitosa: el control falla
    malas = 0
    filas = conn.execute("SELECT tabla, entrada, salida, rechazos FROM bitacora_detalle WHERE id_ejecucion = ?", (ultima,)).fetchall()
    for tabla, entrada, salida, rechazos in filas:
        real = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        if entrada != salida + rechazos or salida != real:
            malas += 1
    return malas


def ejecutar_controles(ruta_db=RUTA_DB):
    conn = conectar(ruta_db)
    resultados = []
    for nombre, sql in CONTROLES_SQL:
        resultados.append((nombre, conn.execute(sql).fetchone()[0]))
    resultados.append(("Nombres: registros con minúsculas", control_mayusculas(conn)))
    resultados.append(("Integridad: PRAGMA foreign_key_check (filas huérfanas)", len(conn.execute("PRAGMA foreign_key_check").fetchall())))
    resultados.append(("Conciliación: tablas donde entrada ≠ salida + rechazos o salida ≠ filas en base", control_conciliacion(conn)))
    conn.close()
    return resultados


if __name__ == "__main__":
    resultados = ejecutar_controles()
    lineas = [f"Controles de calidad - {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for nombre, violaciones in resultados:
        lineas.append(f"[{'PASS' if violaciones == 0 else 'FAIL'}] {nombre}  (violaciones: {violaciones})")
    fallidos = sum(1 for _, v in resultados if v != 0)
    lineas += ["", f"Resumen: {len(resultados) - fallidos} de {len(resultados)} controles OK"]
    texto = "\n".join(lineas)
    print(texto)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(texto, encoding="utf-8")
    sys.exit(1 if fallidos else 0)