"""
Sección 4.5: genera 4 gráficos sencillos a partir de la base de datos.
Uso:  python src/graficos.py      (los PNG quedan en docs/graficos/)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # dibuja a archivo, sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd

from base_datos import conectar, RUTA_DB

CARPETA = Path("docs/graficos")
AZUL, NARANJA, GRIS = "#2F5D8C", "#E08A2E", "#8A8A8A"


def consulta(conn, sql):
    return pd.read_sql(sql, conn)


def etiquetar(ax, barras, formato="{:,.0f}"):
    """Escribe el valor al final de cada barra."""
    for b in barras:
        ancho = b.get_width()
        ax.text(ancho, b.get_y() + b.get_height() / 2, " " + formato.format(ancho), va="center", fontsize=9)


def guardar(fig, nombre):
    CARPETA.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(CARPETA / nombre, dpi=150)
    plt.close(fig)


def grafico_registros_por_tipo(conn):
    df = consulta(conn, "SELECT fuente, tipo, COUNT(*) AS total FROM registro GROUP BY fuente, tipo")
    tabla = df.pivot(index="tipo", columns="fuente", values="total").fillna(0).sort_values("OFAC")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    y = range(len(tabla))
    b1 = ax.barh([i + 0.2 for i in y], tabla["OFAC"], height=0.4, color=AZUL, label="OFAC")
    b2 = ax.barh([i - 0.2 for i in y], tabla["ONU"], height=0.4, color=NARANJA, label="ONU")
    ax.set_yticks(list(y))
    ax.set_yticklabels(tabla.index)
    etiquetar(ax, b1)
    etiquetar(ax, b2)
    ax.set_title("Registros cargados por tipo y fuente (total 20,491)")
    ax.set_xlim(0, tabla["OFAC"].max() * 1.15)
    ax.legend(loc="lower right")
    guardar(fig, "1_registros_por_tipo.png")


def grafico_top_paises(conn):
    df = consulta(conn, "SELECT pais, COUNT(*) AS registros FROM registro_pais GROUP BY pais ORDER BY registros DESC LIMIT 10")
    df = df.iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4))
    barras = ax.barh(df["pais"], df["registros"], color=AZUL)
    etiquetar(ax, barras)
    ax.set_title("Top 10 países con más registros")
    ax.set_xlim(0, df["registros"].max() * 1.15)
    guardar(fig, "2_top_paises.png")


def grafico_rechazos(conn):
    df = consulta(conn, """SELECT tabla || ': ' || motivo AS motivo, COUNT(*) AS filas FROM rechazo
                           WHERE id_ejecucion = (SELECT MAX(id_ejecucion) FROM bitacora_ejecucion WHERE estado = 'OK')
                           GROUP BY tabla, motivo ORDER BY filas""")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    barras = ax.barh(df["motivo"], df["filas"], color=NARANJA)
    etiquetar(ax, barras)
    ax.set_title(f"Filas rechazadas por motivo (total {df['filas'].sum():,})")
    ax.set_xlim(0, df["filas"].max() * 1.15)
    guardar(fig, "3_rechazos_por_motivo.png")


def grafico_cobertura(conn):
    df = consulta(conn, """
        SELECT r.fuente,
               100.0 * SUM(EXISTS (SELECT 1 FROM alias a     WHERE a.id_registro = r.id_registro)) / COUNT(*) AS con_alias,
               100.0 * SUM(EXISTS (SELECT 1 FROM direccion d WHERE d.id_registro = r.id_registro)) / COUNT(*) AS con_direccion,
               100.0 * SUM(EXISTS (SELECT 1 FROM registro_pais p WHERE p.id_registro = r.id_registro)) / COUNT(*) AS con_pais
        FROM registro r GROUP BY r.fuente""").set_index("fuente")
    etiquetas = ["Con alias", "Con dirección", "Con algún país"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = range(len(etiquetas))
    for desplazo, fuente, color in [(-0.2, "OFAC", AZUL), (0.2, "ONU", NARANJA)]:
        barras = ax.bar([i + desplazo for i in x], df.loc[fuente].values, width=0.4, color=color, label=fuente)
        for b in barras:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(etiquetas)
    ax.set_ylim(0, 105)
    ax.set_ylabel("% de registros")
    ax.set_title("Cobertura de datos por fuente")
    ax.legend()
    guardar(fig, "4_cobertura_de_datos.png")


if __name__ == "__main__":
    conn = conectar(RUTA_DB)
    for grafico in (grafico_registros_por_tipo, grafico_top_paises, grafico_rechazos, grafico_cobertura):
        grafico(conn)
    conn.close()
    print(f"Gráficos guardados en {CARPETA}/")