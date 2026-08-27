# Sesión 4 — 2026-08-25 / 27

Sesión larga. Se entró a terminar la Fase 3 y se descubrió que **silver estaba
incompleto desde el principio**: le faltaban 3,58 millones de eventos que
ninguna verificación anterior podía detectar. Se arregló, se reconstruyó gold
entero dos veces, y por el camino aparecieron dos defectos que habrían
publicado números falsos.

## Qué se hizo

**Se resolvió el fallo del temporal de DuckDB.** El `dbt run` con 8 threads y
`memory_limit: "12GB"` generó **594 GiB** de temporal creciendo a 1,71 GiB/min,
dejando el disco del lago en 93 GiB libres: una hora de margen. Se cortó, se
subió el límite a 24 GB y se serializó con `--threads 1` (D34). Con eso el pico
del peor modelo bajó a 301,8 GiB y el temporal se libera entre modelos.

**Se arregló el bug de `silver_todo.py:106`** que la sesión 3 dejó pendiente
(D35), y esta vez se **validó con datos reales**: el reproceso de un día escribió
la línea del registro en el formato nuevo.

**Se ejecutó por fin la reconciliación D26**, pendiente desde la sesión 2.
Resultado: **286 días descuadrados y 3.595.071 filas de menos**. Bronze estaba
completo (las 24 horas de los 361 días, medido), así que la pérdida era del paso
bronze→silver, de escrituras cortadas.

**Se reprocesó silver entero**: 361 días, 0 fallos, 4 h 04 min. Recuperó
3.582.707 filas.

**Se corrigió el criterio de la propia reconciliación.** Los 12.364 restantes no
eran pérdida: eran duplicados de bronze que silver elimina por diseño (D9).
Comparar filas contra filas daba un falso positivo permanente; el invariante
correcto es **ids distintos de bronze contra filas de silver**. Con eso: **0 días
descuadrados, 1.319.383.395 en las dos capas**.

**Se reconstruyó gold** (14 h 42 min) y los tests pasaron de 4 errores a 1, y
después a **40/40 por primera vez en el proyecto**.

**Se explicó el `repo` nulo mirando el JSON crudo**, como exige la regla 1. Se
volvió a descargar `2025-12-01-18.json.gz`: el evento trae `"repo": {}`, vacío
en el origen, y su `forkee` es `private: true`. Son forks a repositorios
privados, donde GitHub no publica el repo. No es un fallo de extracción. Se
excluyen de `dim_repo` con el motivo documentado.

**Se arregló un fallo de precisión que anulaba la pregunta 2.**
`date_diff('minute', ...)` cuenta cruces de frontera, así que toda latencia por
debajo del minuto valía 0. La mediana hasta merge salía 0,00 h para bots **y**
para humanos: la columna borraba justo la diferencia que la pregunta busca.

**Se detectó la degradación de la fuente.** Desde el 2026-03-15 el feed de GH
Archive deja de traer eventos que no sean `PushEvent`: la cuota de PR pasa del
12-14 % estable al 0,13 % en agosto. Está en bronze, es de la fuente. Se recortó
la ventana publicable a **2025-08-13 → 2026-03-14** (D36, D37).

**Se exportaron los agregados** (15,11 MB) y se pasó P2 a minutos.

## Decisiones tomadas

- **D34** · `memory_limit` a 24 GB; el temporal se queda en `D:` por decisión de
  Marcos, con el riesgo anotado.
- **D35** · `silver_todo.py` verifica y anota por día, no por lote.
- **D36** · ventana recortada al 2026-03-14 para las tablas de PR.
- **D37** · la pregunta 3 también se corta, y se corta en el exportador.

## Errores cometidos, y cómo se resolvieron

Todos son el mismo: **decidir sobre una afirmación plausible sin medirla.**

1. **El repo nulo "es un evento suelto".** Eran 12.863, de 9.872 actores. El
   test cuenta filas de la dimensión y una fila agregada esconde miles de
   eventos. → Se midió.

2. **Se culpó al `dropDuplicates` de los huérfanos**, con un mecanismo redondo:
   colisión de ids dentro del mismo día. Los datos lo desmintieron en dos
   consultas — el evento no estaba duplicado, sencillamente faltaba, y ese día
   bronze no tenía **ningún** id repetido. → El culpable eran las escrituras
   cortadas.

3. **El umbral de degradación se puso sobre la cuota de push** (≥80 %), que daba
   2026-05-25. Como las preguntas 1 y 2 viven de los PRs, el detector correcto
   es la cuota de PR, que da **2026-03-15: dos meses antes**. → Corregido antes
   de cortar.

4. **D36 supuso que la pregunta 3 aguantaba** "porque los pushes siguen
   llegando". Medido después: de marzo a julio se pierde el **25 % de actores
   distintos** mientras los eventos suben. Una curva de retención sobre eso
   muestra una fuga que no ocurrió. → D37 lo corrige.

5. **Se estuvo a punto de publicar "los bots mergean 19 veces más rápido".** Al
   partir por clase: `bot_dependencias` tarda 3,2 h, cien veces más que un
   humano, y solo `bot_ci` es instantáneo. El promedio salía rápido porque los
   de CI pesan mucho. → La conclusión simple era falsa.

6. **Se lanzó un escaneo de los 36 GiB de silver** para buscar un dato que
   `dim_repo` ya tenía calculado. Veinte minutos tirados. → Cortado.

7. **Se intentó reescribir seis commits** con un `reset --soft` para arreglar una
   palabra en un mensaje. El sistema lo bloqueó, con razón. → Se dejó como
   estaba.

La lección, más útil que "mide todo": **si vas a decidir algo sobre una
afirmación que no has medido, mídela primero, aunque parezca obvia.** Las cinco
veces, medir costó minutos y el razonamiento estaba mal.

## Estado de los datos

| Capa | Estado |
|---|---|
| `bronze/` | completo, 361 días, 24 h cada uno, 1.319.395.759 filas |
| `silver/` | **completo y verificado**, 1.319.383.395 = ids distintos de bronze |
| `gold/` | completo, `dbt run` y `dbt test` verdes (40/40) |
| agregados | exportados, 15,11 MB, ventana 2025-08-13 → 2026-03-14 |
| dashboard | **todavía publicado con los 6 días de agosto**: falta el push |

## Qué queda pendiente y por dónde se retoma

**Punto exacto de retome: revisar los agregados en
`dashboard/sources/gharchive/` y decidir el push.** Nada se ha publicado.

1. **Decisión abierta**: la tabla resumen de `latencias.md` hace
   `avg(mediana_min_review)`, la media de las medianas mensuales, que no es la
   mediana del periodo. Con meses de volumen desigual (septiembre dobla a
   agosto) el número está mal. Opciones: renombrar la columna para que diga lo
   que es, ponderar por PRs, o exportar la mediana real. La real ya está medida:
   **1,9 min humanos, 0,1 min bots**.
2. **Decisión abierta**: la página de latencias sigue presentando "bot" como un
   bloque. Partirla por clase cambia la conclusión (ver error 5).
3. **`p3_repos_saldo` pesa 15,09 MB** y se regenera entero en cada export. Si el
   cron de la Fase 5 lo commitea a diario, el repo engorda sin parar. Hay que
   decidir si se recorta el grano o si se deja fuera del repo.
4. **Fase 5, replanteada.** D36 la deja tocada: cada día nuevo cae en el tramo
   degradado y no aporta nada a las preguntas 1 y 2. Sigue teniendo sentido para
   la 3, pero hay que decir por qué en el README.
5. **Power BI** y el **README**, que lo escribe Marcos.

## Servicios al cerrar

Comprobado con `Get-CimInstance Win32_Process` filtrando por línea de comandos:

- Sesiones de Spark: **ninguna viva**. Sin procesos de `java`.
- Procesos de `dbt` / DuckDB: **ninguno**.
- Temporal de DuckDB (`gh_archive.duckdb.tmp`): **no existe**, liberado.
- `.spark-staging-*` huérfanos: **ninguno**.
- Descargas, monitores y servidores de Evidence: ninguno.
- Libre en `D:`: 668,6 GiB.
- El `.gz` descargado para verificar el `repo` nulo quedó en el scratchpad de la
  sesión, fuera del repo y del lago.

Nota para futuras comprobaciones:
`tasklist | grep python` **no vale** para verificar que no queda nada del
pipeline: hay procesos de Python de otros proyectos del autor (`AutoPostulator`)
que aparecen ahí. Hay que filtrar por línea de comandos con
`Get-CimInstance Win32_Process`.
