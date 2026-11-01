import sys
from pathlib import Path

# Permite que las pruebas encuentren los módulos de la carpeta src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))