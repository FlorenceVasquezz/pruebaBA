import requests
import pandas as pd 
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

carpeta = Path("data")
carpeta.mkdir(exist_ok=True)

fuentes = {
    "onu": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    "ofac": "https://www.treasury.gov/ofac/downloads/sdn.xml"
}

for nombre, url in fuentes.items():
    respuesta = requests.get(url, headers={"user-agent": "mozilla/5.0"}, timeout=180)
    respuesta.raise_for_status()
    archivo = carpeta / f"{nombre}.xml"
    archivo.write_bytes(respuesta.content)
    print(f"{nombre} : {len(respuesta.content)/1e6:.2f} MB guardados en {archivo}")
    

