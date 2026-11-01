"""
Paso 5: proceso completo.
Lee XML -> transforma -> limpia -> carga en SQLite, con log, bitácora y conciliación.
Se puede ejecutar las veces que se quiera: cada corrida recarga las tablas de datos desde cero.
"""
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from base_datos import conectar, crear_tablas, RUTA_DB
from limpiar import limpiar_todo
from transformar import transformar_ofac, transformar_onu

RUTA_ONU = "data/onu.xml"
RUTA_OFAC = "data/ofac.xml"
TABLAS_DATOS = ["registro", "alias", "direccion", "nacionalidad", "fecha_nacimiento"]
log = logging.getLogger("proceso")


def configurar_log():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler("logs/proceso.log", encoding="utf-8"), logging.StreamHandler()],
    )


def ahora():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def cargar_datos(conn, limpias):
    """Borra lo anterior y carga las tablas limpias. Los hijos se enlazan con id_registro."""
    for t in reversed(TABLAS_DATOS):                 # primero los hijos, al final registro
        conn.execute(f"DELETE FROM {t}")

    limpias["registro"].to_sql("registro", conn, if_exists="append", index=False)

    # SQLite asignó un id_registro a cada fila: lo leemos para enlazar los hijos
    mapa = pd.read_sql("SELECT id_registro, fuente, id_origen FROM registro", conn)
    for t in TABLAS_DATOS[1:]:
        hijos = limpias[t].merge(mapa, on=["fuente", "id_origen"], how="inner")
        hijos = hijos.drop(columns=["fuente", "id_origen"])
        hijos.to_sql(t, conn, if_exists="append", index=False)
        log.info("Cargada tabla %-17s %7d filas", t, len(hijos))


def conciliar(conn, resumen):
    """Controles: entrada = salida + rechazos, y lo cargado = lo limpio, y relaciones sin huérfanos."""
    for _, f in resumen.iterrows():
        if f["entrada"] != f["salida"] + f["rechazos"]:
            raise ValueError(f"Conciliación fallida en {f['tabla']}: "
                             f"{f['entrada']} != {f['salida']} + {f['rechazos']}")
        en_bd = conn.execute(f"SELECT COUNT(*) FROM {f['tabla']}").fetchone()[0]
        if en_bd != f["salida"]:
            raise ValueError(f"{f['tabla']}: en la base hay {en_bd} y se esperaban {f['salida']}")
        log.info("Conciliación OK %-17s entrada=%d salida=%d rechazos=%d", f["tabla"], f["entrada"], f["salida"], f["rechazos"])

    huerfanos = conn.execute("PRAGMA foreign_key_check").fetchall()
    if huerfanos:
        raise ValueError(f"Hay {len(huerfanos)} filas sin padre (integridad referencial)")
    log.info("Integridad referencial OK (0 filas huérfanas)")


def ejecutar():
    configurar_log()
    conn = conectar(RUTA_DB)
    crear_tablas(conn)

    cur = conn.execute("INSERT INTO bitacora_ejecucion (fecha_inicio, fuentes, estado) VALUES (?, ?, 'EN_CURSO')",
                       (ahora(), "ONU,OFAC"))
    id_ejecucion = cur.lastrowid
    conn.commit()
    log.info("=== Inicio ejecución %d ===", id_ejecucion)

    try:
        log.info("Leyendo XML de la ONU: %s", RUTA_ONU)
        onu = transformar_onu(RUTA_ONU)
        log.info("ONU: %d registros leídos", len(onu["registro"]))

        log.info("Leyendo XML de OFAC: %s", RUTA_OFAC)
        ofac = transformar_ofac(RUTA_OFAC)
        log.info("OFAC: %d registros leídos", len(ofac["registro"]))

        limpias, rechazos, resumen = limpiar_todo([onu, ofac])
        log.info("Limpieza terminada: %d filas rechazadas en total", len(rechazos))

        cargar_datos(conn, limpias)

        rechazos.assign(id_ejecucion=id_ejecucion).to_sql("rechazo", conn, if_exists="append", index=False)
        resumen.assign(id_ejecucion=id_ejecucion).to_sql("bitacora_detalle", conn, if_exists="append", index=False)
        conn.commit()

        conciliar(conn, resumen)

        conn.execute("UPDATE bitacora_ejecucion SET fecha_fin=?, estado='OK', mensaje=? WHERE id_ejecucion=?",
                     (ahora(), f"{len(limpias['registro'])} registros cargados, {len(rechazos)} rechazos", id_ejecucion))
        conn.commit()
        log.info("=== Fin ejecución %d: OK ===", id_ejecucion)

    except Exception as error:
        conn.rollback()
        log.exception("La ejecución %d falló", id_ejecucion)
        conn.execute("UPDATE bitacora_ejecucion SET fecha_fin=?, estado='ERROR', mensaje=? WHERE id_ejecucion=?",
                     (ahora(), str(error)[:500], id_ejecucion))
        conn.commit()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    ejecutar()