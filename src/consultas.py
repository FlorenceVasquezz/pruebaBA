"""
Ejecuta las consultas de sql/02_consultas.sql, las muestra y las guarda como CSV.
"""
import re
from pathlib import Path

import pandas as pd

from base_datos import conectar, crear_tablas, RUTA_DB

RUTA_CONSULTAS = Path("sql/02_consultas.sql")
CARPETA_SALIDA = Path("data/output/consultas")


def leer_consultas(ruta=RUTA_CONSULTAS):
    """Separa el archivo en consultas usando las líneas '-- ## nombre'."""
    texto = Path(ruta).read_text(encoding="utf-8")
    trozos = re.split(r"^-- ## (\S+)\s*$", texto, flags=re.M)
    return dict(zip(trozos[1::2], [t.strip() for t in trozos[2::2]]))


if __name__ == "__main__":
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    conn = conectar(RUTA_DB)
    crear_tablas(conn)          # asegura que exista la vista registro_pais
    for nombre, sql in leer_consultas().items():
        df = pd.read_sql(sql, conn)
        df.to_csv(CARPETA_SALIDA / f"{nombre}.csv", index=False, encoding="utf-8-sig")
        print(f"\n===== {nombre}  ({len(df)} filas) =====")
        print(df.head(8).to_string(index=False))
    conn.close()