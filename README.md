# ¿Quién hace el trabajo en GitHub: la gente, los bots o los agentes de IA?

Pipeline analítico sobre **1.319 millones de eventos públicos de GitHub**
(GH Archive, 361 días), construido con PySpark, dbt-duckdb y Evidence, y
publicado sin gastar un euro.

**→ Sitio público: <https://pyspark-gharchive.netlify.app>**
(portada con las respuestas · [BI del propio pipeline](https://pyspark-gharchive.netlify.app/metricas.html) · [dashboard interactivo](https://pyspark-gharchive.netlify.app/dashboard/bots/))

## Las tres preguntas, y lo que salió

Sólo tres. Cualquier métrica que no sirviera a una de ellas se quedó fuera.

| | Pregunta | Respuesta medida |
|---|---|---|
| 1 | ¿Qué parte de la actividad de PRs la generan bots y agentes, y cómo evoluciona? | Del **32,9 %** (ago 2025) al **44,2 %** (mar 2026). Los agentes de IA son el 4,6-7,6 %, al alza; el resto es CI y actualizadores de dependencias. |
| 2 | ¿Cuánto tarda un PR en su primer review y en mergearse? ¿Difiere entre bot y humano? | Humano: **1,8 min** hasta el merge, 18,7 hasta el review. Pero «los bots» no existen: `bot_ci` mergea en 0,1 min y `bot_dependencias` en **184,4**, cien veces más que un humano. Agregarlos invierte la conclusión. |
| 3 | ¿Qué proyectos ganan o pierden contribuyentes? | Entre el **15 y el 19 %** de los contribuyentes nuevos de un repo vuelven al mes siguiente; el 5-7,5 % siguen a los tres meses. Los repos que más gente nueva captan son herramientas de agentes de IA. |

Las conclusiones desarrolladas están en la [portada del sitio](https://pyspark-gharchive.netlify.app/#preguntas).
Cada cifra de este README y del sitio está en [`docs/metrics.md`](docs/metrics.md)
con la fecha en que se midió; ninguna es una estimación.

## Cómo está hecho

```
GH Archive ──httpx──▶ bronze ──PySpark──▶ silver ──dbt-duckdb──▶ gold ──▶ 9 agregados ──▶ sitio + Evidence
 361 días            Parquet zstd        tipado,              estrella:         0,09 MB           Netlify
 8.664 .gz           por fecha           deduplicado,         3 hechos +        (commiteados)
 ~734 GiB/año        149,4 GiB           clase de actor       3 dimensiones
                     1.319 M eventos     40,4 GiB             40 tests
```

| Capa | Herramienta | Qué hace | Dónde |
|---|---|---|---|
| Ingesta | Python + `httpx` | Descarga hora a hora, 6 conexiones como tope, idempotente y reanudable. GH Archive lo mantiene una persona: no se satura. | [`ingest/descargar.py`](ingest/descargar.py), [`backfill.py`](backfill.py) |
| Bronze | PySpark | JSON crudo íntegro en una columna más lo justo para particionar. Inmune a los cambios de formato de la fuente. | [`spark_jobs/bronze.py`](spark_jobs/bronze.py) |
| Silver | PySpark | Tipado, deduplicado por `(id, fecha)`, columnas seleccionadas, clase de actor. Dos tablas: `eventos` y `pr_eventos`. | [`spark_jobs/silver.py`](spark_jobs/silver.py), [`spark_jobs/bots.py`](spark_jobs/bots.py), [`silver_todo.py`](silver_todo.py) |
| Calidad | Python + DuckDB | Unicidad, rango de fechas, 24 horas por día, nulos por esquema, y reconciliación bronze↔silver por día. | [`calidad/tests_calidad.py`](calidad/tests_calidad.py), [`reconciliar.py`](reconciliar.py), [`cobertura_bronze.py`](cobertura_bronze.py) |
| Gold | dbt-duckdb | Esquema en estrella. Grano documentado en el YAML de cada modelo; 40 tests en verde. | [`dbt/models/marts`](dbt/models/marts) |
| Publicación | DuckDB → Parquet/JSON | Nueve agregados (0,09 MB) y dos JSON van al repo; el lago (190 GiB) se queda en casa. | [`exportar_gold.py`](exportar_gold.py), [`exportar_sitio.py`](exportar_sitio.py) |
| Sitio | HTML + Tailwind + ECharts, Evidence | Portada y BI del pipeline a mano; el dashboard de Evidence bajo `/dashboard`. Un solo build en Netlify. | [`site/`](site), [`dashboard/`](dashboard), [`construir_sitio.sh`](construir_sitio.sh) |

Todo corre en un ordenador de sobremesa (Ryzen 7 5800X, 32 GB) con un disco de
250 GB como presupuesto. Ese presupuesto explica casi todas las decisiones de
diseño: el backfill encadena descarga, bronze y borrado del crudo día a día
para que nunca haya más de un día de `.gz` en disco.

## Decisiones y trade-offs

Están todas, con alternativas y coste, en [`docs/decisions.md`](docs/decisions.md)
(D1-D45). Las que más pesan:

- **Bronze guarda el JSON crudo, no un esquema inferido** (D18). La fuente cambió
  de formato el 2025-10-09 sin avisar; un esquema inferido habría partido el
  lago en dos. Silver decide el formato mirando el payload, no la fecha (D12).
- **La deduplicación es por `(id, fecha)`, no por `id`** (D27). El `id` de
  GH Archive se reutiliza: 200 eventos del 2025-11-18 reaparecen con el mismo
  id el 2026-01-23. Deduplicar globalmente borraba eventos reales.
- **Las latencias se calculan restando instantes de eventos, en segundos**
  (D8, y el incidente de `date_diff('minute')`, que ponía a 0 toda latencia
  menor de un minuto y anulaba la pregunta 2).
- **La ventana publicable termina el 2026-03-14** (D36, D37). Desde el día
  siguiente la fuente deja de traer eventos que no sean `PushEvent`: la cuota
  de PR cae del 12 % al 0,13 %. Se detectó midiendo, no está documentado.
- **Hay un tramo sin señal de merge** (D38): del 2025-10-09 al 2025-12-01 la
  fuente no publica si un PR se mergeó, en ninguno de sus tres vocabularios.
  Noviembre tiene cero merges. Las latencias de merge excluyen ese tramo.
- **Los bots nunca se agregan en un bloque** (D40). Por clase, la conclusión de
  la pregunta 2 se invierte.
- **El artefacto público es un sitio estático aparte** (D43), con Evidence en
  un subdirectorio, porque Evidence es bueno para páginas de datos y malo para
  una portada. Power BI se descartó: la BI vive en el sitio.
- **No hay ingesta diaria automatizada, a propósito** (D42). El plan original
  tenía un cron que procesara cada día nuevo y regenerase el dashboard. Se
  descartó al medir que, desde el 2026-03-15, el 99,87 % de lo que publica la
  fuente son `PushEvent`: cada día nuevo cae en el tramo degradado y sólo
  metería ruido en las tres preguntas. Automatizar la ingesta de datos que se
  decide no publicar es un cron por tener un cron. Si la fuente vuelve a emitir
  el resto de eventos, el detector de degradación (`degradacion.py`) es lo que
  reabriría la ventana, y sería lo primero que se pondría a correr solo.

## Lo que salió mal, medido

La parte más útil del proyecto. Todos los incidentes comparten causa: decidir
sobre una afirmación plausible sin haberla medido.

- **Silver estuvo incompleto desde el principio** sin que ningún test lo
  viera: 3.595.071 filas de menos en 286 días por escrituras cortadas. Lo
  detectó la reconciliación por día, ids distintos contra filas. Reproceso
  completo: 4 h 04 min, 3.582.707 filas recuperadas, 0 días descuadrados.
- **El temporal de DuckDB creció a 1,71 GiB/min** hasta 594 GiB con 8 hilos y
  12 GB; quedaba menos de una hora de disco. Con 1 hilo y 24 GB el pico bajó a
  301,8 GiB y `dbt run` terminó en 14 h 42 min.
- **El shuffle de Spark llenó el disco de sistema**: 610,80 GiB en un
  `blockmgr` de un job muerto.
- **El dashboard estuvo tres despliegues publicado sin CSS ni JS**, con el
  workflow en verde. Un build en verde no es un sitio que funciona.

Detalle y cifras en la página de [métricas del pipeline](https://pyspark-gharchive.netlify.app/metricas.html#incidentes)
y en [`docs/metrics.md`](docs/metrics.md).

## Cómo ejecutarlo

Requisitos: Python 3.10, JDK 17, Node 22, y `GHA_DATA_DIR` apuntando a un disco
con sitio (por defecto `D:/gharchive-data`). Windows nativo necesita
`winutils.exe` y `hadoop.dll` (ver [`docs/plan.md`](docs/plan.md), Fase −1).

```bash
pip install -r requirements.txt

# 1. Descarga + bronze, día a día, reanudable. Borra cada .gz al escribirlo.
python backfill.py --desde 2025-08-13 --hasta 2026-08-15

# 2. Silver, día a día, con registro y reanudación.
python silver_todo.py --desde 2025-08-13 --hasta 2026-08-15

# 3. Calidad y reconciliación. Salen con 1 si algo falla.
python calidad/tests_calidad.py --desde 2025-08-13 --hasta 2026-08-15
python reconciliar.py

# 4. Gold. Un hilo a propósito (D34): con 8 el temporal se come el disco.
cd dbt && dbt run --threads 1 && dbt test && cd ..

# 5. Agregados para el sitio y el dashboard (van al repo).
python exportar_gold.py
python exportar_sitio.py
python comprobar_sitio.py      # cada cifra del sitio contra docs/metrics.md

# 6. Sitio completo en dist/ (el mismo script que ejecuta Netlify).
bash construir_sitio.sh
```

El backfill completo tarda unas 3 h de descarga + bronze, 4 h de silver y
15 h de gold en la máquina descrita. El sitio se despliega solo con cada push
a `main`; Netlify construye Evidence y Tailwind en unos 70 s.

## Estructura del repo

```
ingest/            descarga (Fase 1)
spark_jobs/        bronze, silver, clasificación de actores (Fase 2)
calidad/           tests de calidad de silver
dbt/               modelo dimensional (Fase 3)
dashboard/         Evidence: tres páginas, una por pregunta (Fase 4)
site/              portada y BI del pipeline (Fase 4)
docs/
  decisions.md     cada decisión no trivial: qué, alternativas, por qué, coste
  metrics.md       toda cifra del proyecto, con fecha
  exploracion*.md  Fase 0: los datos reales antes de escribir código
  sesiones/        bitácora de cada sesión de trabajo
```

## Fuente y límites

Datos de [GH Archive](https://www.gharchive.org/), un servicio gratuito que
mantiene una persona. En el año medido cambió de formato (2025-10-09), dejó de
publicar la señal de merge durante dos meses y desde 2026-03-15 publica casi
sólo `PushEvent`. Todo eso está tratado en el modelo y explicado en el sitio;
nada se ha rellenado ni estimado. El JSON crudo no está en el repo, ni lo
estará.
