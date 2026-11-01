"""
Explorador genérico de XML.
No asume nada sobre el archivo: descubre solo qué etiquetas trae,
cuáles se repiten (posibles tablas) y cuáles son datos simples (posibles columnas).
"""
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


raiz = ET.parse("data/ofac.xml").getroot()
for e in raiz.iter():
    e.tag = e.tag.split("}")[-1]        
 
tipos = [s.findtext("sdnType") for s in raiz.findall("sdnEntry")]
 
print(set(tipos))        # distinct
print(Counter(tipos))    # distinct con cuántos hay de cada uno

def limpiar_tag(tag):
    # Si la etiqueta trae un prefijo entre llaves {...} (namespace), se lo quitamos
    return re.sub(r"^\{.*?\}", "", tag)


def nuevo_info():
    return {"veces": 0, "tiene_hijos": False, "llenos": 0,
            "max_por_padre": 0, "ejemplos": [], "atributos": set(),
            "valores": set(), "con_espacios": 0}


def recolectar(raiz):
    """Recorre TODO el XML una vez y guarda estadísticas por cada ruta."""
    stats = defaultdict(nuevo_info)

    def recorrer(nodo, ruta):
        info = stats[ruta]
        info["veces"] += 1
        info["atributos"].update(limpiar_tag(a) for a in nodo.attrib)

        if len(nodo):                       # tiene etiquetas hijas -> es un "grupo"
            info["tiene_hijos"] = True
        else:                               # no tiene hijas -> es un "dato"
            crudo = nodo.text or ""
            texto = crudo.strip()
            if crudo != texto:
                info["con_espacios"] += 1       # espacios o saltos de línea al borde
            if texto:
                info["llenos"] += 1
                info["valores"].add(texto)
                if len(info["ejemplos"]) < 3 and texto[:40] not in info["ejemplos"]:
                    info["ejemplos"].append(texto[:40])

        # ¿cuántas veces aparece cada hijo DENTRO de este mismo padre?
        for tag, n in Counter(limpiar_tag(h.tag) for h in nodo).items():
            hijo = stats[ruta + "/" + tag]
            hijo["max_por_padre"] = max(hijo["max_por_padre"], n)

        for h in nodo:
            recorrer(h, ruta + "/" + limpiar_tag(h.tag))

    ruta_raiz = "/" + limpiar_tag(raiz.tag)
    recorrer(raiz, ruta_raiz)
    return stats, ruta_raiz


def explorar(ruta_archivo):
    raiz = ET.parse(ruta_archivo).getroot()
    stats, ruta_raiz = recolectar(raiz)

    print("\n" + "=" * 70)
    print(f"ARCHIVO: {ruta_archivo}")
    print("=" * 70)

    ns = re.match(r"^\{(.*?)\}", raiz.tag)
    print(f"Etiqueta raíz : {limpiar_tag(raiz.tag)}")
    print(f"Namespace     : {ns.group(1) if ns else 'ninguno'}")
    if raiz.attrib:
        print(f"Atributos raíz: {dict((limpiar_tag(k), v) for k, v in raiz.attrib.items())}")

    # ---------- PASO A: el árbol completo ----------
    print("\nA) ÁRBOL: cada etiqueta, cuántas veces aparece y qué tan llena viene")
    print("   'en padre' = en qué % de las filas de su padre aparece esta etiqueta")
    print("   'vacío'    = cuántas veces la etiqueta aparece pero sin texto")
    print(f"{'veces':>7}  {'en padre':>8}  {'vacío':>6}  etiqueta")
    for ruta in sorted(stats):
        i = stats[ruta]
        sangria = "   " * (ruta.count("/") - 1)
        nombre = ruta.split("/")[-1]
        padre = ruta.rsplit("/", 1)[0]
        en_padre = ""
        if padre in stats:
            if i["max_por_padre"] > 1:
                en_padre = f"x{i['max_por_padre']} máx"      # se repite dentro del padre
            else:
                en_padre = f"{100 * i['veces'] / stats[padre]['veces']:.0f}%"
        if i["tiene_hijos"]:
            print(f"{i['veces']:>7}  {en_padre:>8}  {'':>6}  {sangria}[{nombre}]  (grupo)")
        else:
            print(f"{i['veces']:>7}  {en_padre:>8}  {i['veces'] - i['llenos']:>6}  {sangria}{nombre}")

    # ---------- PASO B: candidatas a tabla ----------
    # Regla: una etiqueta que se REPITE dentro de su padre = posible tabla.
    candidatas = [r for r, i in stats.items() if i["max_por_padre"] > 1]
    candidatas.sort(key=lambda r: (r.count("/"), r))

    def padre_candidato(ruta):
        partes = ruta.split("/")
        for k in range(len(partes) - 1, 1, -1):
            if "/".join(partes[:k]) in candidatas:
                return "/".join(partes[:k])
        return None

    print("\nB) TABLAS CANDIDATAS (etiquetas que se repiten) y sus COLUMNAS")
    for cand in candidatas:
        info = stats[cand]
        padre = padre_candidato(cand)
        nombre_tabla = "/".join(cand.split("/")[-2:]) if not info["tiene_hijos"] else cand.split("/")[-1]
        print(f"\n>>> TABLA posible: {nombre_tabla}   "
              f"({info['veces']} filas)   ruta: {cand}")
        print(f"    se relaciona con: {padre.split('/')[-1] if padre else '(es una tabla principal)'}")

        if not info["tiene_hijos"]:
            print("    es una lista de valores simples (1 sola columna: valor)")
            continue

        # Columnas = datos dentro de esta etiqueta, sin cruzar otra tabla candidata
        columnas = []
        for ruta in sorted(stats):
            if not ruta.startswith(cand + "/") or stats[ruta]["tiene_hijos"]:
                continue
            tramo = ruta[len(cand) + 1:].split("/")
            cruza = any((cand + "/" + "/".join(tramo[:k])) in candidatas
                        for k in range(1, len(tramo) + 1))
            if not cruza:
                columnas.append(ruta)

        print(f"    {'columna':<36}{'lleno':>6} {'único':>6}  nota / ejemplos")
        for ruta in columnas:
            i = stats[ruta]
            pct = 100 * i["llenos"] / info["veces"]
            col = ruta[len(cand) + 1:].replace("/", "_")
            unico = "sí" if i["llenos"] and len(i["valores"]) == i["llenos"] else "no"
            nota = []
            if i["llenos"] == 0 or pct < 5:
                nota.append("POCO USO")
            if i["con_espacios"]:
                nota.append(f"ESPACIOS EXTRA({i['con_espacios']})")
            print(f"    {col:<36}{pct:>5.0f}% {unico:>6}  {' '.join(nota)} {i['ejemplos']}")


if __name__ == "__main__":
    archivos = sys.argv[1:] or ["data/onu.xml", "data/ofac.xml"]
    for a in archivos:
        explorar(a)