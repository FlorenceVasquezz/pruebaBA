-- ## 1_conteo_tipo_por_pais
-- Cantidad de registros por país y tipo (un registro cuenta en cada país con el que se relaciona)
SELECT COALESCE(rp.pais, 'SIN PAIS') AS pais,
       r.tipo,
       COUNT(*) AS total
FROM registro r
LEFT JOIN registro_pais rp ON rp.id_registro = r.id_registro
GROUP BY COALESCE(rp.pais, 'SIN PAIS'), r.tipo
ORDER BY pais, total DESC;

-- ## 2_mas_alias
-- Top 20 registros con más alias, desglosado por tipo de alias
SELECT r.fuente, r.id_origen, r.tipo, r.nombre_completo,
       COUNT(*)                         AS total_alias,
       SUM(a.tipo_alias = 'a.k.a.')     AS aka,
       SUM(a.tipo_alias = 'f.k.a.')     AS fka,
       SUM(a.tipo_alias = 'n.k.a.')     AS nka
FROM registro r
JOIN alias a ON a.id_registro = r.id_registro
GROUP BY r.id_registro
ORDER BY total_alias DESC
LIMIT 20;

-- ## 3a_sin_alias
-- Registros que no tienen ningún alias
SELECT r.fuente, r.id_origen, r.tipo, r.nombre_completo
FROM registro r
WHERE NOT EXISTS (SELECT 1 FROM alias a WHERE a.id_registro = r.id_registro)
ORDER BY r.fuente, r.tipo, r.nombre_completo;

-- ## 3b_sin_alias_por_tipo
-- Cuántos registros NO tienen alias de cada tipo (a.k.a., f.k.a., n.k.a.)
SELECT t.tipo_alias, COUNT(*) AS registros_sin_ese_alias
FROM (SELECT 'a.k.a.' AS tipo_alias UNION ALL SELECT 'f.k.a.' UNION ALL SELECT 'n.k.a.') t
CROSS JOIN registro r
WHERE NOT EXISTS (SELECT 1 FROM alias a
                  WHERE a.id_registro = r.id_registro AND a.tipo_alias = t.tipo_alias)
GROUP BY t.tipo_alias;

-- ## 4_top_paises
-- Top 10 países con más registros
SELECT pais, COUNT(*) AS registros
FROM registro_pais
GROUP BY pais
ORDER BY registros DESC
LIMIT 10;

-- ## 5a_nombres_duplicados
-- Mismo nombre completo en más de un registro
SELECT nombre_completo,
       COUNT(*) AS veces,
       GROUP_CONCAT(fuente || ':' || id_origen, ', ') AS registros
FROM registro
GROUP BY nombre_completo
HAVING COUNT(*) > 1
ORDER BY veces DESC, nombre_completo;

-- ## 5b_alias_duplicados
-- Mismo alias en registros distintos
SELECT a.alias,
       COUNT(DISTINCT a.id_registro) AS registros_distintos,
       GROUP_CONCAT(DISTINCT r.fuente || ':' || r.id_origen) AS registros
FROM alias a
JOIN registro r ON r.id_registro = a.id_registro
GROUP BY a.alias
HAVING COUNT(DISTINCT a.id_registro) > 1
ORDER BY registros_distintos DESC, a.alias;

-- ## 5c_alias_igual_a_otro_nombre
-- Alias de un registro que coincide con el nombre completo de OTRO registro
SELECT a.alias,
       rd.fuente || ':' || rd.id_origen AS registro_dueno_del_alias,
       ro.fuente || ':' || ro.id_origen AS registro_con_ese_nombre
FROM alias a
JOIN registro rd ON rd.id_registro = a.id_registro
JOIN registro ro ON ro.nombre_completo = a.alias AND ro.id_registro <> a.id_registro
ORDER BY a.alias;