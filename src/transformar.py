"""
Paso 2: pasar cada XML a DataFrames (tablas).
Aquí SOLO extraemos los datos tal como vienen. La limpieza se hace en el Paso 3.
"""
import re
import xml.etree.ElementTree as ET
import pandas as pd


# ---------- ayudas pequeñas (sirven para los dos XML) ----------
def sin_ns(tag):
    """Quita el prefijo {namespace} de una etiqueta, si lo trae."""
    return re.sub(r"^\{.*?\}", "", tag)


def hijos(nodo, nombre):
    """Hijos directos de 'nodo' cuya etiqueta se llama 'nombre'."""
    return [h for h in nodo if sin_ns(h.tag) == nombre]


def items(nodo, lista, item):
    """Entra a <lista> y devuelve todos sus <item>. Ej: addressList -> address."""
    for contenedor in hijos(nodo, lista):
        yield from hijos(contenedor, item)


def valor(nodo):
    """Texto de una etiqueta. Si viene vacía -> None."""
    return ((nodo.text or "").strip()) or None


def texto(nodo, nombre):
    """Texto de la etiqueta hija 'nombre'. Si no existe o viene vacía -> None."""
    for h in hijos(nodo, nombre):
        return valor(h)
    return None


def unir(*partes):
    """Une partes de texto ignorando las vacías."""
    partes = [p for p in partes if p]
    return " ".join(partes) or None


# ---------- OFAC ----------
def transformar_ofac(ruta):
    raiz = ET.parse(ruta).getroot()
    registro, alias, direccion, nacionalidad, fecha_nac = [], [], [], [], []

    for e in hijos(raiz, "sdnEntry"):
        id_origen = texto(e, "uid")
        base = {"fuente": "OFAC", "id_origen": id_origen}   # enlaza cada fila hija con su padre

        registro.append({**base,
                         "tipo": texto(e, "sdnType"),
                         "nombre": texto(e, "firstName"),
                         "apellido": texto(e, "lastName"),
                         "nombre_extra": None,
                         "fecha_listado": None,
                         "observaciones": texto(e, "remarks")})

        for a in items(e, "akaList", "aka"):
            alias.append({**base,
                          "alias": unir(texto(a, "firstName"), texto(a, "lastName")),
                          "tipo_alias": texto(a, "type"),
                          "calidad": texto(a, "category")})

        for d in items(e, "addressList", "address"):
            direccion.append({**base,
                              "pais": texto(d, "country"),
                              "ciudad": texto(d, "city"),
                              "estado_provincia": texto(d, "stateOrProvince"),
                              "calle": unir(texto(d, "address1"), texto(d, "address2"), texto(d, "address3")),
                              "codigo_postal": texto(d, "postalCode")})

        for n in items(e, "nationalityList", "nationality"):
            nacionalidad.append({**base, "pais": texto(n, "country"), "tipo": "nationality"})
        for n in items(e, "citizenshipList", "citizenship"):
            nacionalidad.append({**base, "pais": texto(n, "country"), "tipo": "citizenship"})

        for f in items(e, "dateOfBirthList", "dateOfBirthItem"):
            fecha_nac.append({**base, "fecha_original": texto(f, "dateOfBirth"), "tipo_fecha": None})

    return {"registro": pd.DataFrame(registro), "alias": pd.DataFrame(alias),
            "direccion": pd.DataFrame(direccion), "nacionalidad": pd.DataFrame(nacionalidad),
            "fecha_nacimiento": pd.DataFrame(fecha_nac)}


# ---------- ONU ----------
def transformar_onu(ruta):
    raiz = ET.parse(ruta).getroot()
    registro, alias, direccion, nacionalidad, fecha_nac = [], [], [], [], []

    # La ONU separa en dos grupos: INDIVIDUALS/INDIVIDUAL y ENTITIES/ENTITY
    for grupo, etiqueta in [("INDIVIDUALS", "INDIVIDUAL"), ("ENTITIES", "ENTITY")]:
        for p in items(raiz, grupo, etiqueta):
            id_origen = texto(p, "DATAID")
            base = {"fuente": "ONU", "id_origen": id_origen}

            registro.append({**base,
                             "tipo": etiqueta,
                             "nombre": texto(p, "FIRST_NAME"),
                             "apellido": texto(p, "SECOND_NAME"),   # supuesto: 2º nombre = apellido (se documenta)
                             "nombre_extra": unir(texto(p, "THIRD_NAME"), texto(p, "FOURTH_NAME")),
                             "fecha_listado": texto(p, "LISTED_ON"),
                             "observaciones": texto(p, "COMMENTS1")})

            for a in hijos(p, f"{etiqueta}_ALIAS"):
                calidad_o_tipo = texto(a, "QUALITY")
                alias.append({**base,
                              "alias": texto(a, "ALIAS_NAME"),
                              # individuos: QUALITY = Good/Low ; entidades: QUALITY = a.k.a./f.k.a.
                              "tipo_alias": calidad_o_tipo if etiqueta == "ENTITY" else None,
                              "calidad": calidad_o_tipo if etiqueta == "INDIVIDUAL" else None})

            for d in hijos(p, f"{etiqueta}_ADDRESS"):
                direccion.append({**base,
                                  "pais": texto(d, "COUNTRY"),
                                  "ciudad": texto(d, "CITY"),
                                  "estado_provincia": texto(d, "STATE_PROVINCE"),
                                  "calle": texto(d, "STREET"),
                                  "codigo_postal": texto(d, "ZIP_CODE")})

            for v in items(p, "NATIONALITY", "VALUE"):
                nacionalidad.append({**base, "pais": valor(v), "tipo": "nationality"})

            for f in hijos(p, "INDIVIDUAL_DATE_OF_BIRTH"):
                desde, hasta = texto(f, "FROM_YEAR"), texto(f, "TO_YEAR")
                rango = f"{desde}-{hasta}" if desde and hasta else None
                fecha_nac.append({**base,
                                  "fecha_original": texto(f, "DATE") or texto(f, "YEAR") or rango,
                                  "tipo_fecha": texto(f, "TYPE_OF_DATE")})

    return {"registro": pd.DataFrame(registro), "alias": pd.DataFrame(alias),
            "direccion": pd.DataFrame(direccion), "nacionalidad": pd.DataFrame(nacionalidad),
            "fecha_nacimiento": pd.DataFrame(fecha_nac)}


if __name__ == "__main__":
    for nombre, funcion, ruta in [("ONU", transformar_onu, "data/onu.xml"),
                                  ("OFAC", transformar_ofac, "data/ofac.xml")]:
        tablas = funcion(ruta)
        print(f"\n===== {nombre} =====")
        for t, df in tablas.items():
            print(f"{t:<18} {df.shape[0]:>7} filas  {df.shape[1]} columnas")
        print(tablas["registro"].drop(columns="observaciones").head(3).to_string())