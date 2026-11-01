# Prueba técnica: Integración de listas de sanciones ONU y OFAC

Carga las listas de sanciones de la ONU y de OFAC en una base SQLite,
las limpia y normaliza, aplica controles de calidad y genera consultas
SQL, gráficos y un resumen ejecutivo.

## Requisitos
- Python 3.10 o superior

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Datos de entrada (carpeta `data/`)
- `ofac.xml`: lista SDN de OFAC (https://www.treasury.gov/ofac/downloads/sdn.xml)
- `onu.xml`: lista consolidada de la ONU,`consolidatedLegacyByPRN.xml`


## Cómo ejecutar
```bash
python src/proceso.py      # carga completa: lee, limpia, guarda y valida
python src/graficos.py     # genera los 4 gráficos en docs/graficos/
pytest                     # corre las pruebas
```
La base queda en `data/output/` y los logs en `logs/`.

## Estructura del proyecto
| Ruta | Contenido |
|---|---|
| `sql/01_schema.sql` | Definición de las tablas |
| `sql/02_consultas.sql` | Las 5 consultas pedidas |
| `src/explorar_xml.py` | Perfilado inicial de los XML |
| `src/carga_xml.py` | Lectura de los XML |
| `src/limpiar.py` | Limpieza y normalización |
| `src/transformar.py` | Conversión al modelo de tablas |
| `src/base_datos.py` | Conexión y creación de la base |
| `src/proceso.py` | Flujo completo (ETL) |
| `src/controles.py` | Controles de calidad y conciliación |
| `src/consultas.py` | Ejecución de las consultas SQL |
| `src/graficos.py` | Gráficos del resumen |
| `tests/` | Pruebas automáticas |
| `docs/` | Gráficos, resultados de controles y documento final |
| `logs/` | Registro de cada ejecución |

## Modelo de datos
- `registro`: una fila por persona, entidad, barco o aeronave (campo `fuente`: ONU u OFAC, y `tipo`).
- `alias`, `direccion`, `registro_pais`: detalle asociado a cada registro.
- `rechazo`: filas descartadas con tabla de origen y motivo.
- `bitacora_ejecucion`: una fila por ejecución, con su estado.

## Resultados de la última ejecución
- 20,491 registros cargados (ONU 1,007 y OFAC 19,484), ninguno rechazado.
- 67,756 filas de detalle; 881 rechazadas (1.3%), casi todas por venir vacías en el origen.
- 14 controles de calidad: todos pasan. Detalle en `docs/resultados_controles.txt`.
- Conciliación: entrada = salida + rechazos en todas las tablas.

## Decisiones y supuestos
- Las filas inválidas no se borran: se guardan en `rechazo` con su motivo.
- Cada ejecución queda en `bitacora_ejecucion`, para comparar versiones de las listas.
- ONU: `SECOND_NAME` se trata como apellido, porque el XML no lo etiqueta.
- ONU: los alias de individuos sin tipo se consideran a.k.a.
- El país de un registro es el conjunto de países de sus direcciones y nacionalidades.
- Los nombres de país de la ONU se igualan a la escritura de OFAC (14 equivalencias manuales).
- Las fechas de nacimiento aproximadas o en rango conservan su fecha inicial, marcadas con su precisión.

## Limitaciones
- Coincidir en nombre entre ONU y OFAC no prueba que sea la misma persona (homónimos).
- Los registros sin país (13.8%) no aparecen en los análisis geográficos.
- Un mismo sujeto puede contarse dos veces al sumar ambas fuentes.