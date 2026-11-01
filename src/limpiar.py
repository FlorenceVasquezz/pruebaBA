"""
Paso 3: limpiar los DataFrames.
Regla de oro: NUNCA se borra nada en silencio. Lo que no pasa va a la tabla de rechazos con su motivo.
"""
import re
from datetime import datetime
import pandas as pd

TIPOS = {"individual": "INDIVIDUO", "entity": "ENTIDAD", "vessel": "BARCO", "aircraft": "AERONAVE"}
TIPOS_ALIAS = {"a.k.a.": "a.k.a.", "f.k.a.": "f.k.a.", "n.k.a.": "n.k.a."}
CALIDAD = {"strong": "FUERTE", "good": "FUERTE", "weak": "DEBIL", "low": "DEBIL"}
# La ONU y OFAC escriben distinto algunos países; unificamos al nombre que usa OFAC
PAISES = {
    "British Virgin Islands": "Virgin Islands, British",
    "China, Hong Kong Special Administrative Region": "Hong Kong",
    "Democratic People's Republic of Korea": "Korea, North",
    "Congo": "Congo, Republic of the",
    "Democratic Republic of the Congo": "Congo, Democratic Republic of the",
    "Iran (Islamic Republic of)": "Iran",
    "Myanmar": "Burma",
    "Russian Federation": "Russia",
    "State of Palestine": "Palestinian",
    "Syrian Arab Republic": "Syria",
    "Türkiye": "Turkey",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United Republic of Tanzania": "Tanzania",
    "United States of America": "United States",
    "Viet Nam": "Vietnam",
}


# ---------- ayudas ----------
def limpiar_texto(s):
    """Quita espacios sobrantes y saltos de línea. Vacío -> None."""
    if not isinstance(s, str):
        return None
    return re.sub(r"\s+", " ", s).strip() or None


def mayusculas(s):
    s = limpiar_texto(s)
    return s.upper() if s else None


def unir(*partes):
    partes = [p for p in partes if isinstance(p, str) and p]
    return " ".join(partes) or None


def rechazos_de(df, mascara, tabla, motivo):
    """Filas que NO pasan: devuelve su registro de rechazo."""
    r = df.loc[mascara, ["fuente", "id_origen"]].copy()
    r["tabla"], r["motivo"] = tabla, motivo
    return r


# ---------- fechas ----------
def _una_fecha(t):
    formatos = (("%d %b %Y", "DIA", "%Y-%m-%d"), ("%Y-%m-%d", "DIA", "%Y-%m-%d"),
                ("%b %Y", "MES", "%Y-%m"), ("%Y", "ANIO", "%Y"))
    for entrada, precision, salida in formatos:
        try:
            d = datetime.strptime(t, entrada)
        except ValueError:
            continue
        if 1850 <= d.year <= datetime.now().year:
            return d.strftime(salida), precision
    return None, None


def parsear_fecha(texto, tipo_fecha=None):
    """Devuelve (fecha_iso, precision). Si no se entiende: (None, 'INVALIDA')."""
    t = limpiar_texto(texto)
    if not t:
        return None, None
    aproximada = bool(re.match(r"circa\s", t, re.I)) or tipo_fecha == "APPROXIMATELY"
    t = re.sub(r"^circa\s+", "", t, flags=re.I)

    if " to " in t or re.fullmatch(r"\d{4}-\d{4}", t):         # rangos
        inicio, fin = re.split(r" to |-", t, maxsplit=1) if " to " in t else t.split("-")
        f1, _ = _una_fecha(inicio.strip())
        f2, _ = _una_fecha(fin.strip())
        return (f1, "RANGO") if f1 and f2 else (None, "INVALIDA")

    fecha, precision = _una_fecha(t)
    if not fecha:
        return None, "INVALIDA"
    return fecha, ("APROXIMADA" if aproximada else precision)


# ---------- una función por tabla ----------
def limpiar_registro(df):
    df = df.copy()
    for c in ["nombre", "apellido", "nombre_extra"]:
        df[c] = df[c].map(mayusculas)
    df["observaciones"] = df["observaciones"].map(limpiar_texto)
    df["tipo"] = df["tipo"].map(limpiar_texto).str.lower().map(TIPOS)

    # Entidades, barcos y aeronaves no tienen apellido: OFAC pone su nombre en "apellido"
    no_persona = df["tipo"] != "INDIVIDUO"
    df.loc[no_persona, "nombre"] = [unir(n, a) for n, a in zip(df.loc[no_persona, "nombre"], df.loc[no_persona, "apellido"])]
    df.loc[no_persona, "apellido"] = None
    df["nombre_completo"] = [unir(n, a, e) for n, a, e in zip(df["nombre"], df["apellido"], df["nombre_extra"])]

    # fecha_listado de la ONU: algunas traen zona horaria (2020-01-01-05:00); nos quedamos con la fecha
    df["fecha_listado"] = [_una_fecha((f or "")[:10])[0] for f in df["fecha_listado"]]

    rech = [rechazos_de(df, df["nombre_completo"].isna(), "registro", "sin nombre"),
            rechazos_de(df, df.duplicated(["fuente", "id_origen"]) & df["nombre_completo"].notna(), "registro", "clave duplicada")]
    malos = df["nombre_completo"].isna() | df.duplicated(["fuente", "id_origen"])
    limpio = df.loc[~malos, ["fuente", "id_origen", "tipo", "nombre", "apellido", "nombre_completo", "fecha_listado", "observaciones"]]
    return limpio, pd.concat(rech)


def _huerfanos(df, registro):
    claves = set(zip(registro["fuente"], registro["id_origen"]))
    return pd.Series([k not in claves for k in zip(df["fuente"], df["id_origen"])], index=df.index)


def limpiar_alias(df, registro):
    df = df.copy()
    df["alias"] = df["alias"].map(mayusculas)
    df["tipo_alias"] = df["tipo_alias"].map(limpiar_texto).str.lower().map(TIPOS_ALIAS).fillna("a.k.a.")  # sin tipo = a.k.a.
    df["calidad"] = df["calidad"].map(limpiar_texto).str.lower().map(CALIDAD)

    vacio = df["alias"].isna()
    huerfano = _huerfanos(df, registro) & ~vacio
    dup = df.duplicated(["fuente", "id_origen", "alias", "tipo_alias"]) & ~vacio & ~huerfano
    rech = [rechazos_de(df, vacio, "alias", "alias vacío"),
            rechazos_de(df, huerfano, "alias", "sin registro padre"),
            rechazos_de(df, dup, "alias", "alias duplicado")]
    return df.loc[~(vacio | huerfano | dup)].copy(), pd.concat(rech)


def limpiar_direccion(df, registro):
    df = df.copy()
    for c in ["pais", "ciudad", "estado_provincia", "calle", "codigo_postal"]:
        df[c] = df[c].map(limpiar_texto)
    df["pais"] = df["pais"].str.replace(r"^Region:\s*", "", regex=True).replace(PAISES)

    columnas = ["pais", "ciudad", "estado_provincia", "calle", "codigo_postal"]
    vacio = df[columnas].isna().all(axis=1)
    huerfano = _huerfanos(df, registro) & ~vacio
    dup = df.duplicated(["fuente", "id_origen"] + columnas) & ~vacio & ~huerfano
    rech = [rechazos_de(df, vacio, "direccion", "dirección sin datos"),
            rechazos_de(df, huerfano, "direccion", "sin registro padre"),
            rechazos_de(df, dup, "direccion", "dirección duplicada")]
    return df.loc[~(vacio | huerfano | dup)].copy(), pd.concat(rech)


def limpiar_nacionalidad(df, registro):
    df = df.copy()
    df["pais"] = df["pais"].map(limpiar_texto)
    df["pais"] = df["pais"].str.replace(r"^Region:\s*", "", regex=True).replace(PAISES)
    df.loc[df["pais"].str.lower().isin(["na", "n/a"]), "pais"] = None    # "na" no es un país

    vacio = df["pais"].isna()
    huerfano = _huerfanos(df, registro) & ~vacio
    dup = df.duplicated(["fuente", "id_origen", "pais", "tipo"]) & ~vacio & ~huerfano
    rech = [rechazos_de(df, vacio, "nacionalidad", "país vacío o inválido"),
            rechazos_de(df, huerfano, "nacionalidad", "sin registro padre"),
            rechazos_de(df, dup, "nacionalidad", "nacionalidad duplicada")]
    return df.loc[~(vacio | huerfano | dup)].copy(), pd.concat(rech)


def limpiar_fecha_nacimiento(df, registro):
    df = df.copy()
    df["fecha_original"] = df["fecha_original"].map(limpiar_texto)
    resultado = [parsear_fecha(t, tf) for t, tf in zip(df["fecha_original"], df["tipo_fecha"])]
    df["fecha"] = [r[0] for r in resultado]
    df["precision"] = [r[1] for r in resultado]

    vacio = df["fecha_original"].isna()
    invalida = (df["precision"] == "INVALIDA")
    huerfano = _huerfanos(df, registro) & ~vacio & ~invalida
    dup = df.duplicated(["fuente", "id_origen", "fecha", "precision"]) & ~vacio & ~invalida & ~huerfano
    rech = [rechazos_de(df, vacio, "fecha_nacimiento", "fecha vacía"),
            rechazos_de(df, invalida, "fecha_nacimiento", "fecha inválida"),
            rechazos_de(df, huerfano, "fecha_nacimiento", "sin registro padre"),
            rechazos_de(df, dup, "fecha_nacimiento", "fecha duplicada")]
    malos = vacio | invalida | huerfano | dup
    return df.loc[~malos, ["fuente", "id_origen", "fecha", "precision", "fecha_original"]].copy(), pd.concat(rech)


# ---------- todo junto ----------
def limpiar_todo(fuentes):
    """fuentes = lista de diccionarios de DataFrames (uno por XML). Devuelve (tablas_limpias, rechazos, resumen)."""
    juntas = {t: pd.concat([f[t] for f in fuentes], ignore_index=True)
              for t in ["registro", "alias", "direccion", "nacionalidad", "fecha_nacimiento"]}

    registro, r1 = limpiar_registro(juntas["registro"])
    alias, r2 = limpiar_alias(juntas["alias"], registro)
    direccion, r3 = limpiar_direccion(juntas["direccion"], registro)
    nacionalidad, r5 = limpiar_nacionalidad(juntas["nacionalidad"], registro)
    fechas, r4 = limpiar_fecha_nacimiento(juntas["fecha_nacimiento"], registro)

    limpias = {"registro": registro, "alias": alias, "direccion": direccion,
               "nacionalidad": nacionalidad, "fecha_nacimiento": fechas}
    rechazos = pd.concat([r1, r2, r3, r5, r4], ignore_index=True)

    resumen = pd.DataFrame([{"tabla": t, "entrada": len(juntas[t]), "salida": len(limpias[t]),
                             "rechazos": int((rechazos["tabla"] == t).sum())} for t in limpias])
    return limpias, rechazos, resumen


if __name__ == "__main__":
    from transformar import transformar_onu, transformar_ofac
    limpias, rechazos, resumen = limpiar_todo([transformar_onu("data/onu.xml"), transformar_ofac("data/ofac.xml")])
    print(resumen.to_string(index=False))
    print("\nMotivos de rechazo:")
    print(rechazos.groupby(["tabla", "motivo"]).size().to_string())