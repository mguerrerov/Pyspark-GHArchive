# Mediciones

Toda afirmación numérica del proyecto sale de esta tabla. Nada estimado.

---

## Fase −1 — Cimientos

Fecha: 2026-08-16.

### Máquina

| Medida | Valor |
|---|---|
| CPU | AMD Ryzen 7 5800X — 8 núcleos / 16 hilos |
| RAM | 31,9 GB |
| Disco C: libre | 90,5 GB |
| Disco D: libre | 1.378,2 GB |
| Sistema | Windows 11 Pro 10.0.26200 |

### Software instalado

| Componente | Versión | Nota |
|---|---|---|
| Python | 3.10.6 | preexistente |
| JDK | Temurin 17.0.20+8 | **64-Bit Server VM**; sustituye al JRE 1.8 de 32 bits que había |
| PySpark | 3.5.3 | wheel de 317,8 MB |
| dbt-core / dbt-duckdb | 1.9.1 / 1.9.1 | |
| DuckDB | 1.1.3 | |
| httpx | 0.28.1 | preexistente |
| winutils / hadoop.dll | rama hadoop-3.3.6 | 119.296 B y 78.848 B; ver D5 |

`winutils.exe` sha256 `496A591E…FD8553` · `hadoop.dll` sha256 `D7AB36A6…0405BE3`.

### Prueba de humo −1.5

Escritura y relectura de Parquet particionado por fecha, `local[4]`, driver 4 GB.

| Intento | Configuración | Resultado |
|---|---|---|
| 1 | JDK 17, sin `HADOOP_HOME` | **Falla** — `FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset` en `Shell.getWinUtilsPath` |
| 2 | + winutils y `HADOOP_HOME` | **Falla** — `SparkException: Python worker failed to connect back` / `SocketTimeoutException: Accept timed out` |
| 3 | + `PYSPARK_PYTHON` al intérprete del venv | **OK** |

Salida del intento 3: `filas escritas=1000 releidas=1000 particiones=2`.

Conclusión: la decisión D1 (Windows nativo) se sostiene. No hace falta WSL2.

### Variables de entorno persistidas (ámbito usuario)

    JAVA_HOME   = C:\Program Files\Eclipse Adoptium\jdk-17.0.20.8-hotspot
    HADOOP_HOME = C:\hadoop

Requieren abrir una terminal nueva para verse. `C:\hadoop\bin` debe estar en el
`PATH` de las sesiones que ejecuten Spark.

---

## Fase 0 — Reconocimiento

Fichero: `2026-08-12-14.json.gz` (miércoles, 14:00–14:59 UTC).
Descargado y analizado en un runner de GitHub Actions (`ubuntu-latest`), porque
la red local no alcanza `data.gharchive.org`; ver D10.

### Fichero

| Medida | Valor |
|---|---|
| Tamaño comprimido | 22.891.223 B (21,83 MiB) |
| Tamaño descomprimido | 111.671.173 B (106,50 MiB) |
| Ratio de compresión | 4,88× |
| Eventos | 162.301 |
| Líneas no parseables | 0 |
| `created_at` mín. / máx. | `14:00:00Z` / `14:59:59Z` |
| `id` duplicados | 1 (`13173052275`, contenido idéntico) |

### Composición

| Medida | Valor |
|---|---:|
| Tipos de evento distintos | 15 |
| `PushEvent` | 148.551 (91,53 %) |
| `PullRequestEvent` | 770 (0,47 %) |
| `PullRequestReviewEvent` | 228 (0,14 %) |
| `IssuesEvent` | 461 (0,28 %) |
| Los 4 tipos de las preguntas de negocio | 1.606 (0,99 %) |
| Eventos de cuentas `[bot]` | 16.547 (10,20 %) |
| Cuentas `[bot]` distintas | 380 |

### Cobertura de campos críticos

| Campo | Cobertura |
|---|---:|
| `payload.pull_request.id` | 100 % (770/770) |
| Lenguaje del repo (4 rutas probadas) | **0 %** |
| Campos temporales del PR | **0 %** |
| `payload.commits` / `size` en `PushEvent` | **0 %** |

### Extrapolación de volumen — ⚠️ SUPERADA

**Obsoleta.** Se conserva por trazabilidad, pero la cifra buena es la medición
de un día completo de la Fase 1: **2,012 GiB/día y ~734 GiB/año**, no los
~940 GiB que se proyectan aquí. La sobreestimación venía de asumir que la hora
punta era representativa; la variación intradía real es de solo 1,35×.

**No es una medición.** Se proyecta desde una única hora punta, así que es una
cota alta.

Hay que proyectar por separado los dos formatos, porque pesan muy distinto: una
hora punta del formato reducido son 21,83 MiB, y del formato completo entre
96 y 122 MiB. La ventana elegida en D11 cae **entera en el formato completo**.

| Horizonte | Formato reducido | Formato completo (~110 MiB/h) |
|---|---:|---:|
| 1 día | ~0,51 GiB | ~2,6 GiB |
| 1 mes | ~15,3 GiB | ~78 GiB |
| 1 año | ~187 GiB | **~940 GiB** |

**Aviso sobre D11.** Con 1.378 GB libres en `D:`, un año de histórico rico en
crudo (~940 GiB en el escenario de hora punta) deja sin sitio a bronze y
silver. El `.gz` se borra en cuanto la hora está en bronze, así que el pico real
es mucho menor que la suma, pero el margen ya no es holgado y depende de que el
borrado vaya al día. Se decide con la medición de un día completo delante:
si no cabe, las salidas son acortar la ventana a seis meses o filtrar tipos de
evento en bronze —donde ahora sí compensa, porque en formato completo el array
de commits de `PushEvent` es lo que más pesa.

### Comparación del esquema entre años

Una hora (14:00–14:59 UTC) de cada año, descargada y analizada en Actions.

| Fecha | Comprimido (MiB) | Eventos | `PullRequestEvent` | `PushEvent` | `[bot]` | Payload |
|---|---:|---:|---:|---:|---:|---|
| 2016-08-17 | 22,20 | 55.106 | 3.580 | 26.490 | 0,00 % | completo |
| 2018-08-15 | 31,27 | 75.426 | 4.878 | 38.065 | 1,12 % | completo |
| 2020-08-12 | 70,51 | 136.958 | 12.487 | 65.011 | 8,51 % | completo |
| 2022-08-17 | 98,26 | 193.991 | 14.390 | 103.021 | 12,47 % | completo |
| 2023-08-16 | 99,47 | 191.032 | 14.197 | 102.666 | 13,68 % | completo |
| 2024-08-14 | 122,55 | 233.812 | 17.235 | 133.065 | 18,09 % | completo |
| 2025-08-13 | 96,48 | 167.303 | 13.181 | 97.403 | 20,30 % | completo |
| 2026-08-12 | 21,83 | 162.301 | 770 | 148.551 | 10,20 % | **reducido** |

Cobertura de `payload.pull_request.base.repo.language` en el tramo completo:
entre **85 % y 92 %**, estable en toda la serie. En el tramo reducido, 0 %.

### Bisección del cambio de formato

Cinco tandas para pasar de un rango de diez años a un día concreto.

| Fecha | Eventos/hora | Payload |
|---|---:|---|
| 2025-09-10 | 168.867 | completo |
| **2025-10-08** | **171.588** | **completo — último observado** |
| 2025-10-09 | 1.346 | reducido |
| 2025-10-10 | 591 | reducido |
| 2025-10-11 | 592 | reducido |
| 2025-10-12 | 595 | reducido |
| 2025-10-13 | 588 | reducido |
| 2025-10-14 | 872 | reducido |
| **2025-10-15** | **141.879** | **reducido — volumen recuperado** |
| 2025-10-16 | 143.988 | reducido |
| 2025-10-17 | 144.571 | reducido |
| 2025-10-18 | 147.168 | reducido |
| 2025-10-19 | 144.785 | reducido |
| 2025-11-12 | 148.543 | reducido |
| 2026-07-08 | 159.060 | reducido |

El cambio de payload ocurre entre el **8 y el 9 de octubre de 2025**, y viene
acompañado de seis días de volumen colapsado (0,4 % de lo esperado) que se
recupera el 15 de octubre.

Resolución del acotamiento: **un día**. Sin bajar a la hora concreta, porque no
cambia ninguna decisión: el tramo entero queda excluido por D13.

---

## Fase 1 — Ingesta

Fecha: 2026-08-16. Ejecutado en `ubuntu-latest` (D10).

### Día completo medido: 2025-08-13 (formato completo)

Sustituye a la extrapolación desde una sola hora punta. **Esto sí es medición.**

| Medida | Valor |
|---|---|
| Horas descargadas | 24 de 24 |
| Horas ausentes (404) | 0 |
| Tamaño del día | 2.160.885.568 B (**2,012 GiB**) |
| Hora más pesada | 104.380.761 B (99,5 MiB) |
| Hora más ligera | 77.055.856 B (73,5 MiB) |
| Media por hora | 90.036.899 B (85,9 MiB) |
| Duración total | 15,2 s con 6 conexiones |
| Suma de tiempos por fichero | 86,8 s |
| Velocidad media | 135,91 MiB/s |

**La variación intradía es mucho menor de lo previsto**: entre la hora más
ligera y la más pesada solo hay un factor de 1,35. La extrapolación anterior
asumía que la hora punta era representativa del pico y que el resto caía mucho
más, y sobreestimaba en un 28 %.

| Proyección | Estimación previa | **Medida** |
|---|---:|---:|
| 1 día | ~2,6 GiB | **2,012 GiB** |
| 1 año | ~940 GiB | **~734 GiB (0,717 TiB)** |

### Verificación de idempotencia

| Pasada | Resumen | Duración |
|---|---|---:|
| Primera | `{'ok': 24}` | 15,2 s |
| Segunda | `{'saltada': 24}` | 0,1 s |

Criterio de aceptación de la fase **cumplido**: la segunda pasada no descarga
nada, no corrompe nada y el manifiesto queda idéntico.

### Advertencia sobre la velocidad

Los 135,91 MiB/s son del ancho de banda de un runner de GitHub, **no de la
máquina del autor**. El tiempo real del backfill depende de la conexión
doméstica y no se ha podido medir por el bloqueo de red (D10). A modo de orden
de magnitud, 734 GiB a 10 MiB/s son unas 21 horas de descarga; a 50 MiB/s, algo
más de 4. No es una cifra del proyecto hasta que se mida.

### Descarga en local con WARP (2026-08-16)

| Medida | Valor |
|---|---|
| Día descargado | 2025-08-13, 24 de 24 horas |
| Bytes | 2.160.885.568 B — **idénticos a los del runner** |
| Duración | 23,2 s con 6 conexiones |
| Velocidad | **88,70 MiB/s** |

La coincidencia byte a byte con la descarga de Actions confirma la integridad.
A esta velocidad, el tiempo de descarga deja de ser una restricción del
proyecto.

---

## Fase 2 — Bronze

Fecha: 2026-08-16. Ryzen 7 5800X, `local[8]`, driver 8 GB.
Día de prueba: 2025-08-13 (formato completo), **3.794.323 eventos**.

### Compresión y proyección: tres configuraciones medidas

| Configuración | Bronze | vs `.gz` | Duración |
|---|---:|---:|---:|
| snappy, JSON de todos los tipos | 3.864.141.412 B (3,599 GiB) | 1,788× | 222,9 s |
| **zstd**, JSON de todos los tipos | 1.850.566.027 B (1,723 GiB) | 0,856× | 135,0 s |
| **zstd + proyección por tipo** | 1.157.963.135 B (**1,078 GiB**) | **0,536×** | **53,3 s** |

Dos hallazgos que no eran obvios:

1. **Con snappy, el Parquet pesa más que el `.gz` de origen** (1,788×). Bronze
   guarda el evento como texto JSON, que es muy redundante, y snappy prioriza
   velocidad sobre ratio. Cambiar a zstd reduce a menos de la mitad **y además
   es más rápido**, porque hay menos bytes que escribir a disco.
2. La proyección por tipo quita otro 37 % y baja la duración a una cuarta parte
   de la configuración inicial.

### Proyección del backfill con estas cifras

| Formato | Bronze por día |
|---|---:|
| Completo (hasta 2025-10-08) | 1,078 GiB |
| Reducido (desde 2025-10-15) | ~0,27 GiB (sin medir, escalado por el tamaño del `.gz`) |

Presupuesto del autor: **250 GB = 232,8 GiB**.

**Silver está sin medir.** La reserva del 15 % que se aplica más abajo es una
provisión, no una medición, y hay que sustituirla en cuanto silver exista.

### Reparto del presupuesto de 250 GB (D19)

| Tramo | Días | Bronze/día | Bronze |
|---|---:|---:|---:|
| A — rico `2025-07-09 → 2025-10-08` | 92 | 1,078 GiB | 99,2 GiB |
| Hueco `2025-10-09 → 10-14` (D13) | 6 | — | 0 |
| B — actual `2025-10-15 → 2026-08-15` | 305 | ~0,27 GiB | ~82,4 GiB |
| **Bronze total** | **397** | | **~181,6 GiB** |
| Provisión de silver (15 %, **sin medir**) | | | ~27,2 GiB |
| **Total** | | | **~208,8 GiB** de 232,8 |

Margen: 10 %. Cobertura temporal: **13 meses**.

El 0,27 GiB/día del tramo B está escalado por el tamaño del `.gz` y **no está
medido**: hay que confirmarlo ejecutando bronze sobre un día del formato nuevo.

### Día del tramo B medido: 2026-08-12 (formato reducido)

| Medida | Valor |
|---|---|
| Descarga | 24 de 24 horas, 530.915.632 B (0,494 GiB), 7,0 s a 72,82 MiB/s |
| Eventos | **3.925.040** |
| Bronze (zstd + proyección) | 99.366.664 B (**0,093 GiB**) |
| Ratio bronze/origen | **0,187×** |
| Duración del job | 15,7 s |

**Tres veces más barato que la estimación** de 0,27 GiB/día. El motivo: en el
formato reducido los `PushEvent` no traen array de commits, y al proyectarlos a
las cinco columnas extraídas queda casi nada. Nótese que tiene **más eventos**
que el día del tramo A (3.925.040 frente a 3.794.323) y ocupa una décima parte.

### Reparto corregido del presupuesto (D19 enmendada)

| Tramo | Días | Bronze/día | Bronze |
|---|---:|---:|---:|
| A — rico `2025-06-01 → 2025-10-08` | 130 | 1,078 GiB (medido) | 140,1 GiB |
| Hueco `2025-10-09 → 10-14` (D13) | 6 | — | 0 |
| B — actual `2025-10-15 → 2026-08-15` | 305 | 0,093 GiB (medido) | 28,4 GiB |
| **Bronze total** | **435** | | **168,5 GiB** |
| Provisión de silver (15 %, sin medir) | | | 25,3 GiB |
| **Total** | | | **193,8 GiB** de 232,8 |

Margen: **17 %**. Cobertura temporal: **14,5 meses**.

El tramo A gana 38 días respecto al reparto anterior gracias a la medición del
tramo B. Silver sigue siendo la única cifra sin medir del cálculo.

---

## Fase 2 — Silver

Fecha: 2026-08-17. Días de prueba: 2025-08-13 (completo) y 2026-08-12 (reducido).

| Medida | Valor |
|---|---|
| Leídas de bronze | 7.719.363 |
| **Duplicados por `id`** | **10** |
| `silver/eventos` | 7.719.353 filas |
| `silver/pr_eventos` | 482.588 filas |
| Duración (2 días) | 100,9 s |

### Tamaño en disco — cierra la última incógnita del presupuesto

| Tabla | Tramo A (2025-08-13) | Tramo B (2026-08-12) |
|---|---:|---:|
| `eventos` | 0,102 GiB | 0,088 GiB |
| `pr_eventos` | 0,022 GiB | 0,001 GiB |
| **Silver total** | **0,124 GiB** | **0,089 GiB** |
| bronze (referencia) | 1,078 GiB | 0,093 GiB |
| silver / bronze | 11,5 % | **96 %** |

El contraste es el esperado: en el tramo A silver es una décima parte de bronze
porque descarta el JSON; en el tramo B bronze ya casi no tiene JSON que
descartar, así que silver pesa casi lo mismo.

**La provisión del 15 % se queda corta.** Silver real son 43,2 GiB para los 435
días, no los 25,3 provisionados.

### Verificación de la detección de esquema (D12)

| Esquema | Filas | `pr_id` | Lenguaje | `pr_abierto_en` | `pr_autor` |
|---|---:|---:|---:|---:|---:|
| completo | 463.458 | 100 % | **91,6 %** | 100 % | 100 % |
| reducido | 19.130 | 100 % | 0 % | 0 % | 0 % |

Cada día cayó en su esquema sin que el código conozca la fecha del cambio.

### `es_merge` unificado entre convenios

| Esquema | Cómo llega el merge | Merges |
|---|---|---:|
| completo | `closed` + `merged=true` | 108.866 |
| reducido | acción `merged` propia | 3.829 |

### Clasificación de actores

| Clase | Eventos | Antes de ampliar listas |
|---|---:|---:|
| humano | 6.268.266 | 6.268.266 |
| bot_ci | 1.093.101 | 1.022.500 |
| bot_dependencias | 202.030 | 202.030 |
| **agente_ia** | **58.614** | 45.293 |
| bot_otro | 97.342 | 181.264 |

Ampliar las listas con lo observado subió `agente_ia` un **29 %** y redujo
`bot_otro` a la mitad. Queda un 1,26 % de eventos en `bot_otro`: es la cola de
cuentas de bajo volumen, y es una limitación conocida del método.

### Tests de calidad

**16 comprobaciones, 16 en verde.**

### Reparto final del presupuesto — todas las cifras medidas

| Concepto | Días | GiB/día | Total |
|---|---:|---:|---:|
| Tramo A bronze | 116 | 1,078 | 125,0 |
| Tramo A silver | 116 | 0,124 | 14,4 |
| Tramo B bronze | 305 | 0,093 | 28,4 |
| Tramo B silver | 305 | 0,089 | 27,1 |
| Crudo transitorio + gold | | | ~7 |
| **Total** | **421** | | **~202 GiB** de 232,8 |

Margen: **13 %**.

---

## Fase 1 bis — El tramo B medido en serie (2026-08-17)

La cifra de 0,093 GiB/día del tramo B salía de **un solo día**, 2026-08-12, y
resultó ser el extremo barato de una serie decreciente. Medido por
`Content-Length` (peticiones HEAD, sin descargar) un día de cada mes:

| Fecha | `.gz` GiB | bronze estimado (×0,52) |
|---|---:|---:|
| 2025-10-15 | 0,824 | 0,429 |
| 2025-11-15 | 0,744 | 0,387 |
| 2025-12-15 | 0,896 | 0,466 |
| 2026-01-15 | 0,855 | 0,445 |
| 2026-02-15 | 0,876 | 0,456 |
| 2026-03-15 | 0,830 | 0,432 |
| 2026-04-15 | 0,737 | 0,383 |
| 2026-05-15 | 0,567 | 0,295 |
| 2026-06-15 | 0,526 | 0,273 |
| 2026-07-15 | 0,484 | 0,252 |
| 2026-08-12 | 0,494 | 0,257 |
| **Media** | **0,712** | **0,370** |

**El tramo B cuesta 113 GiB de bronze, no 28,4.** Casi cuatro veces más. El
volumen de GH Archive cae de forma sostenida desde diciembre de 2025, y tomar
el mes más reciente como representativo subestimaba el resto del año.

Silver del tramo B **no** escala con bronze: depende del número de filas, que se
mantiene en ~3,5 M/día. Se mantiene en ~0,09 GiB/día → 27,5 GiB.

### Reparto final (D19 quater)

| Concepto | Días | GiB/día | Total |
|---|---:|---:|---:|
| Tramo A bronze | 55 | 1,078 | 59,3 |
| Tramo A silver | 55 | 0,124 | 6,8 |
| Tramo B bronze | 305 | 0,370 | 113,0 |
| Tramo B silver | 305 | 0,090 | 27,5 |
| Crudo transitorio + gold | | | ~7 |
| **Total** | **360** | | **~213,6 GiB** de 232,8 |

Margen: **8 %**. Cobertura: **12,5 meses**.

### Prueba del encadenado (10 días sobre el hueco)

| Fecha | Filas | `.gz` GiB | bronze GiB | ratio | s |
|---|---:|---:|---:|---:|---:|
| 2025-10-07 | 3.875.261 | 1,964 | 1,036 | 0,528 | 38,4 |
| 2025-10-08 | 2.769.429 | 1,419 | 0,749 | 0,528 | 29,6 |
| 2025-10-15 | 3.465.925 | 0,824 | 0,429 | 0,521 | 19,8 |
| 2025-10-16 | 3.487.226 | 0,818 | 0,425 | 0,519 | 19,6 |

Los seis días del hueco se saltaron solos. **El 2025-10-08 tiene un 29 % menos
de eventos que el 07**, lo que sugiere que el cambio de formato ocurrió a media
jornada del día 8 y no en la frontera limpia entre el 8 y el 9.

---

## Backfill completo — 2026-08-17

Ejecutado en local con WARP. Encadenado día a día: descarga → bronze → borrado
del crudo.

| Medida | Valor |
|---|---|
| Días procesados | **359** (+1 ya hecho en pruebas = 360) |
| Días fallidos | **0** |
| Días saltados por hueco (D13) | 6 |
| **Eventos** | **1.311.676.396** |
| Bronze en disco | 149,36 GiB |
| Uso total en disco | 153,28 GiB |
| Duración del tramo B | 3,00 h |
| Tiempo de CPU en bronze | 2,34 h (suma por día) |
| Particiones en bronze | 361 |

**El backfill salió más barato de lo proyectado**: 149,36 GiB frente a los
172,2 estimados (55 × 1,078 + 305 × 0,370). La estimación por muestreo mensual
del tramo B sobreestimaba un 13 %, esta vez del lado seguro.

Ninguna partición quedó a medias, no hubo staging huérfano y el crudo se borró
solo, salvo los dos días de pruebas manuales que se ejecutaron sin
`--borrar-crudo` (~3 GiB).

### Incidente: el shuffle llenó el disco de sistema

| Momento | `C:` libre |
|---|---:|
| Inicio de la sesión | 90,5 GB |
| Tras el backfill y silver | **0,5 GB** |
| Tras limpiar los `blockmgr` huérfanos | **611,3 GB** |

Liberados **610,80 GiB**, de los cuales 581,67 en un único `blockmgr` de un job
muerto. Causas y arreglos en D24 y D25.

Efecto del arreglo, mismo rango (7 días, 24.417.900 filas de bronze):

| | Antes | Después |
|---|---|---|
| Resultado | `IOException: Espacio en disco insuficiente` | 2.912.405 filas |
| Duración | abortaba | **112,3 s** |

---

## Silver sobre el backfill completo — 2026-08-17

| Tabla | Particiones | Filas | Disco |
|---|---:|---:|---:|
| `silver/eventos` | 361 | 1.311.676.396 | 37,0 GiB |
| `silver/pr_eventos` | 361 | **99.400.474** | 3,4 GiB |

`pr_eventos` es el 7,6 % de los eventos: los tipos de PR, review e issue.

### Duración por lote (`pr_eventos`)

| Lote | Filas leídas de bronze | Duración |
|---|---:|---:|
| 2025-08-13 → 2025-10-31 | 268.441.080 | 3.908,4 s |
| 2025-11-01 → 2026-01-31 | 325.204.396 | 2.144,8 s |
| 2026-02-01 → 2026-04-30 | 323.560.929 | 2.076,7 s |
| 2026-05-01 → 2026-08-15 | 402.189.354 | **778,8 s** |

El último lote lee **un 50 % más de filas que el primero y tarda cinco veces
menos**. La diferencia es el peso de `evento_json`: el tramo A lo conserva
íntegro y el tramo B apenas lo tiene, y ese texto es lo que domina la lectura.

### Ocupación final frente al presupuesto

| Concepto | GiB |
|---|---:|
| Bronze | 149,4 |
| Silver | 40,4 |
| Crudo de pruebas sin borrar | ~3,0 |
| **Total** | **192,8** de 232,8 |

Margen: **17 %**. El reparto proyectado en D19 quater daba ~213,6 GiB, así que
la realidad quedó un 10 % por debajo.

Discos tras el incidente: `C:` 611,3 GB libres, `D:` 1.229,9 GB libres.

### Conciliación bronze ↔ silver

| Medida | Valor |
|---|---:|
| Filas en bronze | 1.319.395.759 |
| `id` únicos en bronze | 1.319.383.395 |
| **Duplicados reales** | **12.364 (0,0009 %)** |
| `silver/eventos` tras el job interrumpido | 1.308.416.532 |
| **Filas perdidas** | **10.979.227 (0,83 %)** |

La tasa de duplicados confirma lo visto en la Fase 0 (1 de cada 162.301) y
descarta que la diferencia viniera de la deduplicación. Días con **cero**
duplicados perdían igualmente hasta 144.480 filas, lo que señalaba a un
truncamiento del job y no a un filtro.

`silver/eventos` se regeneró por lotes. La comprobación que faltaba está en D26.

### La reutilización de `id` en el formato reducido

Rangos de `id` observados en bronze:

| Día | Formato | `id` mínimo | `id` máximo |
|---|---|---:|---:|
| 2025-08-17 | completo | 53.449.103.959 | 53.467.007.112 |
| 2025-11-18 | reducido | 4.737.530.937 | 6.061.418.692 |
| 2025-12-15 | reducido | 5.293.764.589 | 6.755.921.995 |
| 2026-01-20 | reducido | 5.916.361.921 | 7.661.761.232 |
| 2026-08-12 | reducido | 13.136.792.391 | 17.522.520.212 |

En el formato completo el rango de un día es estrecho y monótono creciente,
como corresponde a un identificador global. En el reducido los rangos son
anchos y **se solapan entre meses**.

Prueba directa: de los 99.408 eventos que desaparecían del 2025-11-18, se
tomaron 200 y los 200 reaparecen el **2026-01-23** como eventos distintos.

| | 2025-11-18 | 2026-01-23 |
|---|---|---|
| Tipos | `PushEvent`, `CreateEvent`, `DeleteEvent` | `IssuesEvent`, `PullRequestEvent`, `WatchEvent`… |

Colisiones medidas entre pares de días concretos: **0** entre 2025-11-18 y
2025-12-15, **0** entre 2025-11-18 y 2026-01-20, **0** entre 2025-12-15 y
2025-12-16. Las reutilizaciones no siguen la cercanía temporal.

Impacto de deduplicar globalmente por lote:

| Ámbito | Filas | Perdidas |
|---|---:|---:|
| Bronze lote 2 (nov–ene) | 325.204.396 | — |
| `id` únicos en todo el lote | 322.969.287 | 2.235.109 |
| Silver escrito | 322.969.287 | — |

Silver coincidía **exactamente** con los ids únicos del lote: el job hacía lo
que se le pidió, y lo que se le pedía estaba mal.

## Silver completo — 2026-08-17

Medido con DuckDB sobre `silver/**/*.parquet` (`group by event_date`), no
estimado ni tomado del registro de ejecución.

| | Valor |
|---|---:|
| Días con datos | 361 (2025-08-13 → 2026-08-15) |
| Días del rango sin bronze, saltados | 7 |
| Particiones vacías o sin Parquet | 0 |
| Días descuadrados entre `eventos` y `pr_eventos` | 0 |
| Filas en `silver/eventos` | 1.315.800.688 |
| Filas en `silver/pr_eventos` | 99.400.474 |

Tamaño en disco de las tres capas, misma fecha:

| Capa | GiB | Sobre bronze |
|---|---:|---:|
| `bronze/` | 150,53 | 1,000× |
| `silver/eventos` | 36,05 | 0,239× |
| `silver/pr_eventos` | 3,31 | 0,022× |

El recuento de silver supera en 4.124.292 filas los 1.311.676.396 eventos que
la sesión 2 anotó para bronze, pero **las dos cifras no son comparables**: la de
bronze cubre 359 días y esta 361. No se ha medido el recuento de bronze sobre
los mismos 361 días, así que la conciliación bronze↔silver de D26 sigue siendo
la única prueba de que no falta ni sobra nada, y hay que ejecutarla.

## Derrame a disco del `dbt run` completo — 2026-08-25

Run lanzado a las 11:12 con `threads: 8` y `memory_limit: "12GB"`, con los cinco
marts corriendo a la vez sobre `stg_eventos` (vista sobre los 1.315.800.688
eventos de silver). Cortado a mano a las ~18:05, sin haber terminado ningun
mart, tras 6 h 53 min.

| | Valor |
|---|---:|
| Temporal acumulado al cortar | 594 GiB |
| Ritmo de crecimiento medido | 1,71 GiB/min |
| Libre en `D:` al cortar | 93 GiB |
| Margen restante hasta llenar el disco | ~54 min |

El ritmo se midio en una ventana de 60 s: el temporal crecio 1.712.128 KiB y el
espacio libre de `D:` bajo exactamente esos mismos 1.712.128 KiB, lo que
descarta que `du` estuviera contando ficheros dispersos.

Dos observaciones del mismo run:

- `dim_fecha` tardo **10,72 s**. En el intento del 2026-08-24, con el temporal
  en disputa entre conexiones, el mismo modelo tardo **2.925 s**: 273x mas.
- Al matar el proceso, DuckDB **no** limpio su temporal. Los 594 GiB siguieron
  ocupados hasta borrarlos a mano.

Pendiente de medir: el pico de temporal de un solo mart con `--threads 1` y
`memory_limit: "24GB"` (D34), y cual de los cinco aporta la mayor parte.

## `dbt run` completo sobre el ano entero — 2026-08-25/26

Run con `--threads 1`, `memory_limit: "24GB"` (D34) y `--exclude dim_fecha`.
Arrancado a las 19:05 del 25, terminado a las 09:14 del 26.
**`PASS=7 WARN=0 ERROR=0`, 50.940,96 s (14 h 09 min).**

Duracion y pico de temporal por modelo. El pico se midio muestreando el
directorio de spill cada 2 min; el temporal se libera entero al terminar cada
modelo, cosa que con 8 threads no pasaba.

| Modelo | Fuente | Duracion | Pico temporal |
|---|---|---:|---:|
| `dim_actor` | `stg_eventos` (1.315 M) | 2 h 00 min | 106,8 GiB |
| `fct_actividad_contribuyente` | `stg_eventos` (1.315 M) | 7 h 11 min | 301,8 GiB |
| `dim_repo` | `stg_eventos` (1.315 M) | 4 h 20 min | 179,5 GiB |
| `fct_pr_ciclo` | `stg_pr_eventos` (99,4 M) | 29 min 34 s | 22,3 GiB |
| `fct_pr_evento` | `stg_pr_eventos` (99,4 M) | 8 min 07 s | 0 GiB |
| `dim_fecha` | (excluido; medido antes) | 10,72 s | — |

Lo que manda es **la fuente, no el tipo de modelo**: los tres que escanean los
1.315 millones de eventos van de 2 a 7 horas, y los dos que solo tocan los 99,4
millones de `pr_eventos` bajan a menos de media hora. `dim_repo` es una
dimension y cuesta 4 h 20 min porque saca los repos distintos del escaneo
completo.

Comparado con el intento de 8 threads y 12 GB: pico de 301,8 GiB en el peor
modelo frente a 594 GiB acumulados y creciendo, y el disco nunca bajo de
384,9 GiB libres.

### Recuentos de gold tras el run

| Tabla | Filas |
|---|---:|
| `dim_fecha` | 368 |
| `dim_actor` | 29.523.325 |
| `dim_repo` | 90.149.859 |
| `fct_pr_evento` | 99.400.474 |
| `fct_pr_ciclo` | 52.370.476 |
| `fct_actividad_contribuyente` | 171.440.783 |

`fct_pr_evento` coincide **exactamente** con las 99.400.474 filas de
`silver/pr_eventos`. Rango de fechas `2025-08-13 → 2026-08-15` en `dim_fecha` y
en `fct_pr_evento`.

## Reconciliacion bronze <-> silver (D26, por fin ejecutada) — 2026-08-26

Contando filas por particion en las dos capas con `reconciliar.py` (solo
lectura). Detalle por dia en `docs/reconciliacion.json`.

| | Valor |
|---|---:|
| Filas en `bronze` | 1.319.395.759 |
| Filas en `silver/eventos` | 1.315.800.688 |
| **Filas que faltan en silver** | **3.595.071 (0,27 %)** |
| **Dias descuadrados** | **286 de 361** |

Reparto por mes, que muestra que el fallo es **episodico y no sistematico**:

| Mes | Dias desc. | Faltan | % del mes | Peor dia |
|---|---:|---:|---:|---|
| 2025-08 | 1 | 9 | 0,00 % | 2025-08-13 (9) |
| 2025-09 | 7 | 18 | 0,00 % | 2025-09-04 (5) |
| 2025-10 | 18 | 3.533 | 0,01 % | 2025-10-22 (1.498) |
| 2025-11 | 30 | 1.579.739 | 1,49 % | 2025-11-18 (99.409) |
| 2025-12 | 24 | 786 | 0,00 % | 2025-12-05 (218) |
| 2026-01 | 30 | 654.584 | 0,62 % | 2026-01-24 (37.875) |
| 2026-02 | 28 | 774.412 | 0,79 % | 2026-02-03 (72.479) |
| 2026-03 | 19 | 22.857 | 0,03 % | 2026-03-02 (14.570) |
| 2026-04 | 30 | 451.767 | 0,41 % | 2026-04-12 (32.189) |
| 2026-05 | 31 | 53.966 | 0,05 % | 2026-05-03 (16.162) |
| 2026-06 | 23 | 40.116 | 0,05 % | 2026-06-07 (22.126) |
| 2026-07 | 30 | 6.713 | 0,01 % | 2026-07-04 (1.917) |
| 2026-08 | 15 | 6.571 | 0,01 % | 2026-08-07 (5.609) |

Verificado en un dia concreto que la perdida no viene de la transformacion:
el 2026-01-10 bronze tiene 3.524.899 filas y **3.524.899 ids distintos**, o sea
que el `dropDuplicates(["evento_id","event_date"])` no descarta nada, y aun asi
silver tiene 3.505.279 (19.620 menos). Un evento concreto (`5726077108`,
`rajesh7291/crud_2`) esta en bronze y en `silver/pr_eventos`, y **no esta** en
`silver/eventos`.

### Por que las verificaciones anteriores no lo vieron

La sesion 3 dio silver por completo contando **particiones** (361, ninguna
vacia) y D32 reconstruyo el registro desde el disco con ese mismo criterio.
Ninguna de las dos compara **filas** contra bronze, asi que una particion corta
pasa las dos. Es el motivo por el que D26 estaba pendiente y por el que
`metrics.md` decia que la comparacion de la sesion 3 "no vale".

### Consecuencia en gold

Los 4 tests de dbt que fallan el 2026-08-26 son sintoma de esto:

| Test | Fallos |
|---|---:|
| `not_null_dim_repo_repo` | 1 fila (agrega 12.863 eventos con `repo` nulo, 2025-12-01 -> 2026-08-14) |
| `relationships_fct_pr_ciclo_repo -> dim_repo` | 638 |
| `relationships_fct_pr_evento_repo -> dim_repo` | 651 |
| `relationships_fct_pr_evento_actor -> dim_actor` | 241 |

Las dimensiones salen de `stg_eventos` y los hechos de PR de
`stg_pr_eventos`. Como la perdida afecta a `eventos` y no a `pr_eventos`, hay
claves en los hechos que no existen en su dimension. Los huerfanos visibles
(638) son solo los que cayeron en repos sin ningun otro evento: el conjunto real
de eventos ausentes es de 3,6 millones.

El `repo` nulo es un asunto **distinto y sin diagnosticar**: 12.863 eventos con
`repo_name` nulo en bronze desde el 2025-12-01. Pendiente de mirar en los datos
crudos.

## Cobertura horaria de bronze (Fase 2) — 2026-08-26

Medida con `cobertura_bronze.py` sobre `created_at`. Detalle en
`docs/cobertura_bronze.json`.

| | Valor |
|---|---:|
| Dias en bronze | 361 |
| Pares (dia, hora) | 8.664 = 361 x 24 |
| **Dias sin las 24 horas** | **0** |
| Horas presentes pero anormalmente cortas | 27 |

**Bronze esta completo en cobertura.** Por tanto las 3.595.071 filas que
faltan en silver no vienen de la ingesta: se pierden en el paso bronze ->
silver, y se recuperan reprocesando, sin volver a descargar.

Las 27 horas cortas (menos de un tercio de la mediana de filas de su dia) se
agrupan en tardes concretas y con recuperacion en la hora siguiente, el patron
de una caida de la fuente:

| Tramo | Horas afectadas |
|---|---|
| 2025-09-08 | 17:00 -> 23:00 |
| 2025-10-08 | 17:00 -> 23:00 |
| 2025-11-02 | 08:00 |
| 2026-06-02 a 2026-06-05 | franjas de tarde y madrugada |

Son incidencias de GH Archive, no del pipeline, y **no explican el descuadre**:
de los 30 dias descuadrados de noviembre solo el 2025-11-02 aparece aqui. Es
una limitacion de la fuente que la serie temporal del dashboard debe declarar.

## El `repo` nulo: verificado en el JSON crudo — 2026-08-26

`dim_repo` tiene una fila con `repo` nulo que agrega **12.863 eventos** de
9.872 actores distintos, del 2025-12-01 al 2026-08-14. Para saber si era un
fallo de extraccion se volvio a descargar el fichero horario
`2025-12-01-18.json.gz` (31.888.060 B) y se abrio.

| | Valor |
|---|---:|
| Eventos en ese fichero | 150.483 |
| Eventos sin `repo.name` | **1** |
| Coincide con lo que bronze marco nulo | si |

El evento `5019583753` (`ForkEvent`, actor `ChristineG29`) trae literalmente:

    "repo": {},

**El objeto viene vacio en el origen.** `bronze.py:64` extrae `$.repo.name`,
que es la ruta correcta: el campo no existe, no es que se lea mal. En ese mismo
evento el `payload.forkee` tiene `"private": true`, lo que sugiere que GitHub
omite la identidad del repo cuando el fork apunta a un repositorio privado. Eso
explicaria que **todos** los nulos del 2025-12-01 sean `ForkEvent` (9 de 9).

Comprobado en **un** evento: que los 12.863 sean todos forks a privado es
coherente pero **no esta medido**. Lo que si esta establecido es que el dato no
viene en la fuente y no hay nada que corregir en la ingesta.

## Reproceso de silver y reconciliacion corregida — 2026-08-26

`silver_todo.py --desde 2025-08-13 --hasta 2026-08-15 --rehacer
--dias-por-lote 1`: **361 dias, 0 fallos, 244,4 min (4 h 04 min)**, ~38 s/dia
en el tramo de formato completo y ~25 s/dia en el reducido.

| | Antes | Despues |
|---|---:|---:|
| Filas en `silver/eventos` | 1.315.800.688 | **1.319.383.395** |
| Descuadre contra filas de bronze | 3.595.071 | 12.364 |
| Dias descuadrados | 286 | 194 |

### Los 12.364 restantes NO son perdida

Son duplicados legitimos de bronze que silver elimina por diseno (D9). Medido
dia a dia, la coincidencia es exacta:

| Dia | Filas bronze | Ids distintos | Duplicados | "Faltan" en silver |
|---|---:|---:|---:|---:|
| 2025-08-13 | 3.794.323 | 3.794.314 | 9 | 9 |
| 2025-10-15 | 3.465.925 | 3.465.793 | 132 | 132 |
| 2025-10-20 | 3.502.555 | 3.502.281 | 274 | 274 |

Que estos numeros salieran **identicos** antes y despues de rehacer el dia
desde cero fue la pista: un corte no se reproduce al digito, una
deduplicacion si.

**El criterio de reconciliacion estaba mal, no los datos.** Comparaba filas de
bronze contra filas de silver; el invariante correcto es **ids distintos de
bronze** contra filas de silver. `reconciliar.py` queda corregido, porque si no
la Fase 5 heredaria una comprobacion que da falsos positivos para siempre.

### Que fallaba de verdad, entonces

Las 3.582.707 filas recuperadas si eran perdida real, de escrituras de silver
que se cortaron (la sesion 3 documenta cinco cortes). No las detecto nadie
porque las verificaciones existentes contaban particiones, no filas.

### Reconciliacion definitiva (criterio corregido) — 2026-08-26

| | Valor |
|---|---:|
| Ids distintos en `bronze` | 1.319.383.395 |
| Filas en `silver/eventos` | 1.319.383.395 |
| **Dias descuadrados** | **0 de 361** |

Primera vez en el proyecto que silver queda verificado contra bronze fila a
fila. Sustituye a todas las cifras de volumen anteriores: el recuento bueno de
silver es **1.319.383.395**, no los 1.315.800.688 de la sesion 3.

## Run y test definitivos sobre silver completo — 2026-08-27

`dbt run --threads 1`: **PASS=8 ERROR=0, 52.942 s (14 h 42 min)**.
`dbt test --threads 1`: **PASS=39 ERROR=1, 1.296 s (21 min 36 s)**.

Tiempos por modelo, contra el run del 2026-08-26 sobre el silver incompleto:

| Modelo | Run 1 | Run 2 |
|---|---:|---:|
| `dim_actor` | 2 h 00 min | 2 h 24 min |
| `fct_actividad_contribuyente` | 7 h 11 min | 7 h 17 min |
| `dim_repo` | 4 h 20 min | 4 h 19 min |
| `fct_pr_ciclo` | 29 min 34 s | 31 min 27 s |
| `fct_pr_evento` | 8 min 07 s | 8 min 54 s |
| `dim_fecha` | 10,72 s | 72,96 s |

Cuatro de seis repiten tiempo casi exacto. `dim_actor` se desvia 24 min sin que
el 0,27 % de filas nuevas lo explique: quedan **dos medidas distintas**, no se
promedian.

Recuentos, contra el run anterior:

| Tabla | Run 1 | Run 2 |
|---|---:|---:|
| `dim_actor` | 29.523.325 | 29.545.318 |
| `dim_repo` | 90.149.859 | 90.233.267 |
| `fct_actividad_contribuyente` | 171.440.783 | 171.739.758 |
| `fct_pr_ciclo` | 52.370.476 | 52.370.476 |
| `fct_pr_evento` | 99.400.474 | 99.400.474 |

Las dos de PR no cambian, coherente con que la perdida estaba en `eventos` y no
en `pr_eventos`.

### Los tests: prediccion cumplida

Se predijo antes de ejecutar que desapareceran los tres fallos de relaciones y
seguira el del `repo` nulo. Ocurrio exactamente eso: **de 4 errores a 1**. Los
huerfanos eran consecuencia de los eventos que faltaban en silver, no un fallo
del modelo dimensional. El error que queda es `not_null_dim_repo_repo`, 1 fila,
los forks a repositorios privados.

## Fallo de precision en la pregunta 2 — 2026-08-27

`fct_pr_ciclo.sql:84,89` calcula las latencias con
`date_diff('minute', ...) / 60.0`. En DuckDB `date_diff` cuenta cruces de
frontera, asi que **todo lo que ocurre en menos de un minuto se aplasta a 0**.

Efecto medido sobre `cohorte_madura`:

| | Mediana review | Mediana merge | PRs con merge = 0 exacto |
|---|---:|---:|---:|
| bot/agente | 0,07 h | **0,00 h** | 1.204.562 (esquema completo) |
| humano | 0,27 h | **0,03 h** | 1.216.297 (esquema reducido) |

Verificado en un PR concreto: `EnkiBoss/Sesame-TK-F` #2741096008 abre a las
00:22:07 y mergea a las 00:22:41 del 2025-08-13. Son **34 segundos** reales y
la columna guarda 0.

Recalculado con precision de segundos (septiembre 2025):

| | PRs | Mediana merge | p75 | Bajo 1 min |
|---|---:|---:|---:|---:|
| bot/agente | 514.419 | **5 s** | 0,66 h | 63 % |
| humano | 956.446 | **101 s** | 0,81 h | 45 % |

**El truncado no era solo impreciso: borraba la respuesta a la pregunta 2.** La
diferencia entre bot y humano es de un factor 20 y la columna actual la reduce
a cero en ambos.

Aviso sobre esas cifras: estan **sesgadas a la baja** porque la consulta filtra
eventos de septiembre, y los PRs abiertos en septiembre y mergeados despues
quedan fuera. Es la misma censura que diagnostico la sesion 2. Las cifras
publicables salen de `cohorte_madura` sobre el año entero, y requieren
arreglar el modelo antes.
