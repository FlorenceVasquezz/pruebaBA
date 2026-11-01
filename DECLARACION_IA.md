# Declaración de uso de inteligencia artificial

Prueba técnica: Ingeniero Junior de Datos (LAFTFPA) | Cláusula 7

**Herramienta:** Claude (Anthropic), mediante chat.

**Finalidad:** apoyo para entender el enunciado, como explorar los xml y recibir sugerencias sobre el diseño de tablas, el código de carga, las consultas SQL, los controles, los gráficos y la redacción de la documentación.

**Partes con asistencia:** `sql/01_schema.sql`, `sql/02_consultas.sql`, `src/` (carga, limpieza, controles, gráficos), el documento final y el README. En todos los casos fue apoyo: yo ejecuté, probé y ajusté el contenido.

**Cómo lo verifiqué:**
- Ejecuté el código en mi equipo y corrí los 14 controles de calidad y las pruebas con `pytest`.
- Comparé las cifras del resumen con la base de datos. Así detecté y corregí una afirmación inexacta sobre los registros sin alias.
- Revisé y asumí los supuestos y recomendaciones del resumen ejecutivo.
- Decisiones propias: [completar con 1 o 2, por ejemplo por qué las filas vacías van a `rechazo` en lugar de eliminarse].

**Datos:** solo usé las listas públicas de la ONU y de OFAC indicadas en la prueba. No ingresé credenciales, archivos internos ni otra información.

**Declaración:** Utilicé Claude como apoyo para entender el enunciado y recibir sugerencias de diseño, código y redacción. La asistencia se aplicó en los archivos listados arriba. Revisé el resultado mediante ejecución del código, controles de calidad, pruebas y comparación con la base de datos. Asumo la responsabilidad sobre la versión final entregada y puedo explicar y modificar cualquier parte de ella.

Florence Vasquez, 1 de noviembre de 2026
