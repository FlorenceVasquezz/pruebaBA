"""
Pruebas automatizadas del proceso (sección 4.4).
Usan datos pequeños inventados, así que corren en segundos y no dependen de los XML grandes.
Ejecutar:  pytest -v
"""
import pandas as pd

from limpiar import limpiar_alias, limpiar_registro, limpiar_todo, parsear_fecha


# ---------- ayudas para armar datos de prueba ----------
def registro_df(filas):
    columnas = ["fuente", "id_origen", "tipo", "nombre", "apellido", "nombre_extra", "fecha_listado", "observaciones"]
    return pd.DataFrame(filas, columns=columnas)


def un_registro(fuente="OFAC", id_origen="1", tipo="Individual", nombre="Juan", apellido="Perez"):
    return (fuente, id_origen, tipo, nombre, apellido, None, None, None)


# ---------- Prueba 1: validación de fechas ----------
def test_fechas_se_normalizan_y_las_invalidas_se_detectan():
    assert parsear_fecha("10 Dec 1948") == ("1948-12-10", "DIA")            # formato OFAC -> ISO
    assert parsear_fecha("Dec 1948") == ("1948-12", "MES")                  # solo mes y año
    assert parsear_fecha("1948") == ("1948", "ANIO")                        # solo año
    assert parsear_fecha("circa 07 Jul 1966") == ("1966-07-07", "APROXIMADA")
    assert parsear_fecha("32 Jan 2000") == (None, "INVALIDA")               # día imposible
    assert parsear_fecha("1700") == (None, "INVALIDA")                      # año fuera de rango


# ---------- Prueba 2: normalización de nombres ----------
def test_nombres_se_normalizan_a_mayusculas_y_entidades_no_tienen_apellido():
    df = registro_df([
        un_registro(id_origen="1", nombre="juan  carlos", apellido="pérez"),
        # OFAC guarda el nombre de las entidades en "apellido": debe pasar a "nombre"
        un_registro(id_origen="2", tipo="Entity", nombre=None, apellido="acme   corp "),
    ])
    limpio, rechazos = limpiar_registro(df)
    persona, entidad = limpio.iloc[0], limpio.iloc[1]

    assert persona["nombre_completo"] == "JUAN CARLOS PÉREZ"
    assert entidad["tipo"] == "ENTIDAD"
    assert entidad["nombre"] == "ACME CORP" and pd.isna(entidad["apellido"])
    assert rechazos.empty


# ---------- Prueba 3: alias (homologación y rechazos) ----------
def test_alias_se_homologan_y_los_invalidos_van_a_rechazos():
    registro_ofac, _ = limpiar_registro(registro_df([un_registro(fuente="OFAC", id_origen="1")]))
    registro_onu, _ = limpiar_registro(registro_df([un_registro(fuente="ONU", id_origen="1")]))
    registros = pd.concat([registro_ofac, registro_onu])

    alias = pd.DataFrame([
        ("OFAC", "1", "  juancho ", "a.k.a.", "strong"),   # válido: se limpia y homologa
        ("OFAC", "1", "JUANCHO", "a.k.a.", "strong"),      # duplicado del anterior
        ("OFAC", "1", None, "a.k.a.", "weak"),             # alias vacío
        ("OFAC", "9", "FANTASMA", "a.k.a.", "weak"),       # su registro no existe
        ("ONU", "1", "X", None, "Low"),                    # ONU individuo: sin tipo -> a.k.a.
    ], columns=["fuente", "id_origen", "alias", "tipo_alias", "calidad"])

    limpios, rechazos = limpiar_alias(alias, registros)

    assert len(limpios) == 2
    assert limpios.iloc[0]["alias"] == "JUANCHO" and limpios.iloc[0]["calidad"] == "FUERTE"
    assert limpios.iloc[1]["tipo_alias"] == "a.k.a." and limpios.iloc[1]["calidad"] == "DEBIL"
    assert sorted(rechazos["motivo"]) == ["alias duplicado", "alias vacío", "sin registro padre"]


# ---------- Prueba 4: conciliación entrada = salida + rechazos ----------
def test_conciliacion_entrada_es_igual_a_salida_mas_rechazos():
    registro = registro_df([
        un_registro(id_origen="1"),
        un_registro(id_origen="1"),                                 # clave repetida -> rechazo
        un_registro(id_origen="2", nombre=None, apellido=None),     # sin nombre -> rechazo
    ])
    vacias = {
        "alias": pd.DataFrame(columns=["fuente", "id_origen", "alias", "tipo_alias", "calidad"]),
        "direccion": pd.DataFrame(columns=["fuente", "id_origen", "pais", "ciudad", "estado_provincia", "calle", "codigo_postal"]),
        "nacionalidad": pd.DataFrame(columns=["fuente", "id_origen", "pais", "tipo"]),
        "fecha_nacimiento": pd.DataFrame(columns=["fuente", "id_origen", "fecha_original", "tipo_fecha"]),
    }
    _, rechazos, resumen = limpiar_todo([{"registro": registro, **vacias}])

    assert (resumen["entrada"] == resumen["salida"] + resumen["rechazos"]).all()
    fila = resumen[resumen["tabla"] == "registro"].iloc[0]
    assert (fila["entrada"], fila["salida"], fila["rechazos"]) == (3, 1, 2)
    assert len(rechazos) == 2