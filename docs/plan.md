# Plan de desarrollo — pipeline analítico sobre GH Archive

Documento vivo. Se actualiza al cerrar cada fase.
Fecha de redacción: 2026-08-16.

---

## 0. Estado de partida (medido, no supuesto)

Repositorio vacío salvo la especificación del proyecto. No hay git inicializado.

| Recurso | Valor observado | Implicación |
|---|---|---|
| CPU | AMD Ryzen 7 5800X — 8 núcleos / 16 hilos | Spark local holgado. Paralelismo objetivo: 8–12 particiones activas |
| RAM | 31,9 GB | Permite driver de 8–12 GB sin ahogar el sistema |
| Disco C: | 90,5 GB libres | Insuficiente para el lago de datos |
| Disco D: | 1.378 GB libres | **Aquí va `data/`**, fuera del repo |
| Python | 3.10.6 | Compatible con PySpark 3.5.x y 4.0.x |
| Paquetes | solo `httpx` 0.28.1, `pandas` 2.3.3 | Todo lo demás por instalar |
| Java | 1.8.0_431, **JRE**, `os.arch=x86`, 32 bits | **Blocker** |
| Node | v22.14.0 | Suficiente para Evidence.dev |
| git | 2.49.0.windows.1 | Falta `git init` y remoto |

### Blockers a resolver antes de escribir una línea de pipeline

1. **JVM.** Hay un JRE de 32 bits. Un proceso de 32 bits topa en ~1,5 GB de heap
   independientemente de los 32 GB de la máquina, y PySpark necesita un JDK, no
   un JRE. Sin esto no hay Fase 2. Solución: JDK 17 x64 (Temurin), y
   `JAVA_HOME` apuntando a él explícitamente para que Spark no coja el de 32
   bits que ya está en el `PATH`.
2. **Escritura de Parquet en Windows nativo.** Spark usa la capa Hadoop de
   ficheros, que en Windows exige `winutils.exe` + `hadoop.dll` en
   `HADOOP_HOME`. Es una fuente clásica de fallos opacos. Alternativa: correr
   todo el backfill dentro de WSL2. Decisión abierta (ver §6).
3. **Repositorio público.** El criterio de éxito nº 1 es una URL permanente.
   Eso obliga a repo público en GitHub con Pages activado. Decisión abierta.

---

## 1. Arquitectura objetivo

```
GH Archive (.json.gz horario)
        │  httpx, ≤6 conexiones, reintentos + backoff
        ▼
  data/raw/YYYY-MM-DD/HH.json.gz        (D:, gitignored, efímero)
        │  PySpark — lectura ndjson
        ▼
  data/bronze/  event_date=YYYY-MM-DD/  (Parquet, crudo)
        │  PySpark — tipado, dedup por id, is_bot
        ▼
  data/silver/  event_date=YYYY-MM-DD/  (Parquet, columnar y estrecho)
        │  dbt-duckdb — lee Parquet con read_parquet()
        ▼
  gold/  esquema en estrella  →  gh_archive.duckdb + parquets agregados
        │                          (pequeños → sí entran en el repo)
        ├──► Evidence.dev  →  build estático  →  GitHub Pages
        └──► Power BI (.pbix + capturas)
```

Puntos de diseño que sostienen esta forma:

- **El `.gz` es efímero.** Se borra en cuanto la hora está confirmada en bronze
  (regla del proyecto). Bronze es la fuente de verdad reproducible.
- **La frontera Spark/DuckDB está en silver.** Spark hace el trabajo pesado y
  distribuido (cientos de GB de JSON); DuckDB hace el modelado dimensional
  sobre un volumen ya reducido en dos o tres órdenes de magnitud. Cada motor
  donde gana.
- **Solo el gold entra en el repo.** Son agregados: MB, no GB. Esto es lo que
  hace que Evidence pueda construirse en Actions sin acceso al lago.

---

## 2. Estructura de ficheros

```
.
├── README.md                  ← lo escribe Marcos
├── .gitignore                 ← data/, *.gz, *.duckdb grandes, .venv
├── requirements.txt
├── ingest/
│   └── descargar.py           Fase 1
├── spark_jobs/
│   ├── bronze.py              Fase 2
│   └── silver.py              Fase 2
├── calidad/
│   └── tests_calidad.py       Fase 2 — unicidad, rango, cobertura 24h, nulos
├── dbt/                       Fase 3 — proyecto dbt-duckdb
│   ├── models/staging/
│   └── models/marts/
├── dashboard/                 Fase 4 — Evidence.dev
├── powerbi/                   Fase 4 — .pbix + capturas
├── docs/
│   ├── plan.md                ← este documento
│   ├── exploracion.md         Fase 0
│   ├── decisions.md           transversal
│   └── metrics.md             transversal
└── .github/workflows/
    ├── diario.yml             Fase 5
    └── pages.yml              Fase 4
```

La ruta del lago se lee de una variable de entorno (`GHA_DATA_DIR`, por defecto
`D:/gharchive-data`) para que nada dependa de rutas absolutas del portátil.

---

## 3. Fases

### Fase −1 — Cimientos (nueva, precede a todo)

No estaba en la especificación inicial pero sin esto la Fase 0 no puede ni
ejecutarse.

| # | Tarea | Criterio de aceptación |
|---|---|---|
| −1.1 | `git init`, `.gitignore`, primer commit | `git status` limpio; `data/` ignorado |
| −1.2 | Crear repo público en GitHub y push | URL viva |
| −1.3 | Instalar JDK 17 x64 y fijar `JAVA_HOME` | `java -version` reporta 64-Bit Server VM |
| −1.4 | `.venv` + `requirements.txt` | `import pyspark` sin error |
| −1.5 | Humo de Spark: crear DF, escribir Parquet, releer | Fichero Parquet en disco, conteo correcto |

−1.5 es el que valida de verdad el punto 2 de los blockers. Si falla ahí,
migramos a WSL2 antes de invertir nada más.

### Estado: COMPLETADA el 2026-08-16

Las cinco tareas hechas y verificadas. Detalle de las cifras en `metrics.md`.

- Repo público: https://github.com/mguerrerov/Pyspark-GHArchive
- JDK: Temurin 17.0.20, **64-Bit Server VM**. El JRE de 32 bits queda anulado
  por `JAVA_HOME`.
- −1.5 necesitó dos correcciones, ambas registradas como decisiones: winutils
  con `HADOOP_HOME` (D5) y `PYSPARK_PYTHON` fijado en código (D6). Pasa en
  verde: 1.000 filas escritas y releídas en 2 particiones.
- **D1 se confirma**: Windows nativo funciona, no hace falta WSL2.

**Checkpoint humano.**

---

### Fase 0 — Reconocimiento

Regla dura del proyecto: **ningún esquema se escribe sin haber mirado datos
reales**. Aquí no se escribe pipeline, se escribe un informe.

Fichero a inspeccionar: una hora reciente y representativa (ni festivo, ni
madrugada — una franja laboral europea entre semana).

Entregable `docs/exploracion.md`:

1. Tamaño comprimido, tamaño descomprimido, ratio, número de eventos.
2. Tipos de evento presentes y frecuencia absoluta y relativa.
3. Esquema completo observado del `payload` de `PullRequestEvent`,
   `PullRequestReviewEvent`, `IssuesEvent` y `PushEvent`, con un ejemplo real
   íntegro de cada uno.
4. **Verificación explícita del lenguaje del repo** en `PullRequestEvent`:
   ¿existe?, ¿en qué ruta exacta?, ¿qué tasa de nulos tiene? Es supuesto
   crítico de la pregunta de negocio 1 y no se da por bueno.
5. Duplicados por `id` dentro del fichero: cuántos, y si los hay, si el
   contenido es idéntico o difiere.
6. Truncamiento del array de commits en `PushEvent`: comparar `len(commits)`
   contra el campo de tamaño y reportar el umbral observado.

Añado tres verificaciones más, porque el diseño de las tres preguntas de
negocio depende de ellas y salen gratis en la misma pasada:

7. Señales de bot disponibles: ¿existe `actor.login` con sufijo `[bot]`?
   ¿hay un campo de tipo de usuario en el payload? ¿con qué cobertura?
8. Campos temporales del PR: `created_at`, `merged_at`, `closed_at` — ¿en qué
   acciones aparecen poblados? Sin esto no hay pregunta 2.
9. Identificador estable de PR entre eventos distintos: ¿qué campo permite unir
   un `PullRequestEvent` con sus `PullRequestReviewEvent`?

### Estado: COMPLETADA el 2026-08-16

Los nueve puntos cubiertos. Entregable en `exploracion.md` (conclusiones) más
`exploracion_datos.md` y `exploracion_historico.md` (anexos generados).

El hallazgo central no estaba previsto: **GH Archive cambió de formato el
2025-10-09** y desde entonces sirve los payloads recortados. Acotado por
bisección en cinco tandas sobre Actions, de un rango de diez años a un día.
Trae además seis días de volumen colapsado (2025-10-09 → 10-14) que se
recuperan el día 15.

Decisiones derivadas: D11 (ventana `2024-10-09 → 2025-10-08`), D12 (soportar
ambos esquemas detectando por campos), D13 (excluir el tramo degradado), D14.
Y D7 queda revocada: el lenguaje del repo **sí** está en el histórico rico, al
~90 %.

**Checkpoint humano.**

---

### Fase 1 — Ingesta

Descarga idempotente y reanudable de un rango de fechas.

- Concurrencia máxima **6**. GH Archive lo mantiene una persona y es gratuito.
- Reintentos con backoff exponencial y jitter.
- Idempotencia por manifiesto: un fichero de estado registra cada hora
  descargada con su tamaño y checksum. Reejecutar salta lo ya hecho.
- Distinguir el 404 legítimo (hora que GH Archive nunca publicó — las hay) del
  fallo transitorio, y registrarlo como hueco conocido en vez de reintentar en
  bucle.
- Descarga en `.part` y renombrado atómico al terminar, para que una
  interrupción no deje un `.gz` truncado que parezca completo.

Criterio de aceptación: ejecutar dos veces seguidas el mismo rango; la segunda
no descarga nada, no corrompe nada, y el manifiesto es idéntico.

### Estado: IMPLEMENTADA y validada en Actions el 2026-08-16

`ingest/descargar.py` cumple el criterio de aceptación: primera pasada
`{'ok': 24}`, segunda `{'saltada': 24}` en 0,1 s.

De paso resuelve la incógnita del volumen con una medición en vez de una
extrapolación: un día completo son **2,012 GiB**, que proyectan **~734 GiB al
año**, y eso confirma la ventana de D11 (D15).

**Pendiente**: no se ha ejecutado nunca en la máquina del autor, por el bloqueo
de red de D10. El backfill sigue bloqueado ahí, no en el código.

**Checkpoint humano.**

---

### Fase 2 — Bronze y Silver

**Bronze** — Parquet particionado por fecha, sin transformar.

Tensión a resolver aquí: "crudo" a volumen completo puede ser inasumible en
disco. La salida propuesta es filtrar por *tipo de evento* (no por campos):
bronze conserva los eventos íntegros de los tipos que sirven a las tres
preguntas, y descarta el resto. Se registra como decisión con su coste: si más
adelante hiciera falta otro tipo de evento, hay que reingerir. Se decide con
las cifras de la Fase 0 delante.

**Silver** — tipado, deduplicado por `id`, columnas seleccionadas, flag `is_bot`.

La detección de bots es la decisión de diseño más delicada del proyecto, porque
es literalmente la pregunta de negocio 1. Capas previstas, de más fiable a
menos:

1. Sufijo `[bot]` en el login — señal fuerte de GitHub App.
2. Campo de tipo de usuario en el payload, si la Fase 0 confirma que existe.
3. Lista explícita de bots conocidos de alto volumen (dependabot, renovate,
   github-actions, y los que aparezcan al medir).
4. Agentes de codificación asistida por IA — categoría aparte, no "bot"
   clásico. Es la parte interesante y la que puede no ser resoluble solo con
   los datos del evento. Se decide con evidencia, y si no es resoluble se dice
   en el README en vez de inventar una heurística frágil.

Cada capa se etiqueta por separado, no se colapsa en un booleano opaco.

**Tests de calidad obligatorios**: unicidad de `id`, `created_at` dentro del
rango esperado, cobertura de las 24 horas de cada día, tasa de nulos por
columna. Fallan ruidosamente y bloquean la promoción a gold.

Borrado del `.gz` en cuanto la hora está escrita en bronze, con verificación
previa de conteo.

### Estado: COMPLETADA el 2026-08-17

`bronze.py`, `silver.py`, `bots.py` y `calidad/tests_calidad.py` funcionando y
medidos sobre dos días reales, uno de cada formato. **16 comprobaciones de
calidad en verde.**

Silver escribe dos tablas: `eventos` (todos los eventos tipados, sostiene la
pregunta 3) y `pr_eventos` (payload de PR extraído, sostiene las preguntas 1 y
2). La detección de esquema de D12 funciona: cada día cayó en el suyo sin que el
código conozca la fecha del cambio.

La clasificación de actores pasó de booleano a cinco clases (D21). Los
timestamps se fuerzan a UTC (D22) y los tests vigilan tasas de nulos en vez de
exigir cero (D23).

**Pendiente**: el backfill no se ha lanzado. Falta el script que encadene
descargar → bronze → borrar crudo día a día, porque bajar los 435 días de golpe
son ~412 GiB y no caben en el presupuesto de D16.

**Checkpoint humano.**

---

### Fase 3 — Gold y modelo dimensional

Estrella explícita en dbt-duckdb. Grano documentado en el YAML de cada modelo.

Dimensiones: `dim_repo`, `dim_actor`, `dim_fecha`, `dim_tipo_evento`.
Hechos, uno por pregunta de negocio:

- `fct_pr_evento` — grano: un evento de PR. Sirve a la pregunta 1.
- `fct_pr_ciclo` — grano: un PR. Columnas de latencia: apertura → primer
  review, apertura → merge. Sirve a la pregunta 2.
- `fct_actividad_contribuyente` — grano: actor × repo × mes. Sirve a la 3.

**Riesgos analíticos a tratar aquí explícitamente, no a ignorar:**

- *Censura por el borde de la ventana.* Los PRs abiertos cerca del final del
  histórico aún no se han mergeado. Calcular una media de "tiempo hasta merge"
  sin corregir esto la sesga a la baja. Tratamiento: cohortar por fecha de
  apertura y excluir las cohortes sin madurar, diciéndolo en el dashboard.
- *Censura por el borde inicial.* Los PRs mergeados al principio de la ventana
  se abrieron antes de que empiece, y su evento de apertura no está. Mismo
  tratamiento por el otro lado.
- *Cohortes de retención.* Un "contribuyente nuevo" solo es nuevo respecto a la
  ventana observada; alguien activo desde 2019 parecerá nuevo si la ventana
  empieza en 2025. Hay que llamarlo por su nombre en el dashboard.
- *GH Archive no es la API.* Son eventos, no snapshots. Un PR cuyo ciclo de
  vida cruza un hueco de datos queda incompleto. Los huecos conocidos de la
  Fase 1 se propagan hasta aquí como metadato.

Tests de dbt en las claves: `unique`, `not_null`, `relationships`.

### Estado: COMPLETADA el 2026-08-17

Estrella en dbt-duckdb: **8 modelos y 40 tests en verde**. Tres hechos, uno por
pregunta, con el grano documentado en el YAML. Ninguna clave es de una sola
columna (D27). Decisiones D28–D31.

**Checkpoint humano.**

---

### Fase 4 — Dashboard

Evidence.dev, tres páginas, una por pregunta de negocio. Ni una métrica más.

- Fuente de datos: los parquets gold commiteados, no el lago.
- Despliegue en GitHub Pages vía Actions.
- Power BI como BI secundario: `.pbix` + capturas en el repo.

Criterio de aceptación literal del proyecto: **un desconocido abre la URL y
entiende algo en 10 segundos, sin clonar nada.**

### Estado: EN LÍNEA desde el 2026-08-17

**https://mguerrerov.github.io/Pyspark-GHArchive/**

Cuatro páginas —portada más una por pregunta— construidas desde los Parquet
agregados que exporta `exportar_gold.py` y que sí viven en el repo, porque el
runner no tiene acceso al lago. El cambio de formato y el hueco de octubre se
avisan en la propia interfaz.

**Pendiente**: los datos publicados son todavía los de la ventana de
desarrollo. Al terminar la regeneración de silver hay que reejecutar dbt,
exportar y hacer push. Y los gráficos habrá que afinarlos con datos reales.

**Checkpoint humano.**

---

### Fase 5 — Automatización

Workflow con cron diario que procesa el día anterior de forma incremental.

**Replanteada tras D36 y D42.** La versión original regeneraba también el
dashboard. Ya no: desde el 2026-03-15 la fuente no publica eventos que no sean
`PushEvent`, así que cada día nuevo cae en el tramo degradado y no aporta nada
a las preguntas 1 y 2 —y, medido en D37, tampoco a la 3—. El cron descarga,
escribe bronze y silver, y ejecuta `degradacion.py` para publicar la cobertura
y avisar si la fuente se recupera. La ventana publicada sigue congelada en el
2026-03-14 y el dashboard solo se regenera a mano. Lo que la fase demuestra es
que la orquestación existe y corre sola, que es lo que tiene que demostrar; la
publicación automática no se puede justificar con estos datos.

Incógnita a medir, no a suponer: si PySpark cabe en un runner gratuito de
Actions (2 vCPU, ~7 GB RAM, ~14 GB disco) para 24 ficheros horarios. Si no
cabe, plan B: en el incremental diario, DuckDB lee el ndjson comprimido
directamente y escribe silver; Spark se queda para el backfill masivo local,
que es donde de todos modos demuestra lo que tiene que demostrar. La decisión
se toma con un tiempo cronometrado, y se registra en `decisions.md` como
trade-off, que es exactamente el tipo de cosa que el README debe contar.

**Checkpoint humano — cierre.**

---

## 4. Documentos transversales

`docs/decisions.md` — cada decisión no trivial en 5 líneas: qué decidí, qué
alternativas había, por qué esa, qué me cuesta. Ya identificadas como
pendientes: clave de particionado, filtrado de tipos en bronze, formato de
silver, Parquet vs Delta, detección de bots, tratamiento de duplicados, corte
del histórico, motor del incremental diario, tratamiento de la censura.

`docs/metrics.md` — toda afirmación numérica sale de aquí: filas procesadas,
duración del job, tamaño en disco antes y después, ratio de compresión. Una
tabla por fase.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Volumen del backfill mayor de lo asumible | Alto | Se dimensiona la ventana **después** de medir en Fase 0, no antes |
| Spark en Windows nativo falla al escribir | Alto | Humo en −1.5 antes de invertir; salida a WSL2 |
| El lenguaje del repo no está en el payload | Medio | Se verifica en Fase 0; si no está, la pregunta 1 se reformula sin corte por lenguaje |
| PySpark no cabe en runner de Actions | Medio | Plan B DuckDB para el incremental |
| Bots de IA no distinguibles con los datos del evento | Medio | Se reporta como limitación en vez de heurística inventada |
| Saturar GH Archive | Alto (ético) | 6 conexiones tope, backoff, sin reintentos agresivos |

---

## 6. Decisiones

Cerradas el 2026-08-16 (detalle en `decisions.md`):

1. **Entorno de ejecución**: Windows nativo con JDK 17 x64 + winutils.
2. **Repositorio**: público en GitHub, creado con `gh` bajo la cuenta
   `mguerrerov`.
3. **Alcance de la Fase 0**: una sola hora, como pide la especificación.
4. **Lago de datos**: `D:/gharchive-data`, vía `GHA_DATA_DIR`.

Cerradas tras la Fase 0:

5. **Ventana histórica**: `2024-10-09 → 2025-10-08` (D11), sujeta a que quepa
   en disco según la medición de un día completo.
6. **Dos esquemas** soportados por detección de campos (D12).
7. **Bronze no filtra por tipo de evento**, salvo que el volumen obligue. En el
   formato reducido guardarlo todo es barato; en el completo el array de
   commits de `PushEvent` es lo que más pesa, y ahí sí sería la primera palanca.

Siguen abiertas:

8. **El bloqueo de red (D10)**, que impide correr la ingesta en local. Bloquea
   la Fase 1.
9. **Si un año de histórico rico cabe en `D:`**, con el borrado del `.gz` tras
   escribir bronze como mecanismo que lo hace viable.
