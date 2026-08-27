# Decisiones

Cada entrada en cinco líneas: qué decidí, qué alternativas había, por qué esa,
qué me cuesta.

---

## D1 — Entorno de ejecución: Windows nativo con JDK 17 x64

- **Qué**: el backfill de PySpark corre en Windows nativo, no en WSL2.
- **Alternativas**: WSL2 (Ubuntu), que se parece más al runner de Actions.
- **Por qué**: la máquina ya está montada ahí y el lago cabe en `D:` sin la
  penalización de acceso que WSL sufre sobre `/mnt/d`.
- **Coste**: hay que instalar `winutils.exe` y `hadoop.dll`, y la capa Hadoop
  en Windows produce errores opacos. Se valida con la prueba de humo −1.5.
- **Reversible**: sí. Si −1.5 falla, se migra a WSL2 antes de invertir más.

## D2 — Repositorio público en GitHub desde el inicio

- **Qué**: repo público creado con `gh` bajo `mguerrerov`.
- **Alternativas**: git solo local hasta tener algo que enseñar.
- **Por qué**: el criterio de éxito nº 1 es una URL permanente, y GitHub Pages
  y los minutos ilimitados de Actions solo aplican en repos públicos.
- **Coste**: todo el historial es visible desde el primer commit, incluidos los
  tanteos. Obliga a no commitear nunca datos crudos ni secretos.

## D3 — Fase 0 sobre un único fichero horario

- **Qué**: la exploración inicial se hace sobre una sola hora.
- **Alternativas**: una hora de tres momentos separados en el tiempo, para
  detectar cambios de esquema a lo largo del histórico.
- **Por qué**: es lo que pide la especificación del proyecto y mantiene el
  checkpoint corto.
- **Coste**: un cambio de esquema en el histórico no se detecta ahora; puede
  aparecer a mitad del backfill. Se mitiga en la Fase 2 haciendo que la lectura
  de bronze falle ruidosamente ante un campo inesperado, en vez de silenciarlo.

## D4 — Lago de datos en `D:/gharchive-data`

- **Qué**: `raw/`, `bronze/` y `silver/` viven en `D:`, fuera del repo.
- **Alternativas**: `C:`, o un subdirectorio del propio proyecto.
- **Por qué**: `C:` tiene 90 GB libres y `D:` 1.378 GB. Fuera del repo, además,
  hace imposible commitear datos crudos por accidente.
- **Coste**: la ruta no es portable. Se absorbe leyéndola de `GHA_DATA_DIR`,
  con `D:/gharchive-data` solo como valor por defecto.

## D5 — winutils de terceros para desbloquear Spark en Windows

- **Qué**: `winutils.exe` y `hadoop.dll` de `cdarlint/winutils` (rama
  hadoop-3.3.6) en `C:\hadoop\bin`, con `HADOOP_HOME` fijado.
- **Alternativas**: migrar a WSL2 (plan B de D1), o compilar winutils desde las
  fuentes de Hadoop con Visual Studio.
- **Por qué**: la prueba de humo −1.5 confirmó que sin ellos Spark no escribe
  Parquet en Windows. Es el atajo estándar y mantiene D1 en pie; compilar son
  horas para un proyecto de portfolio.
- **Coste**: son binarios mantenidos por un particular, no por Apache, y la
  versión 3.3.6 no coincide exactamente con el Hadoop 3.3.4 que empaqueta
  PySpark 3.5.3. Verificado en la práctica: escribe y relee Parquet
  particionado sin error. Reversible borrando `C:\hadoop`.

## D6 — `PYSPARK_PYTHON` se fija en código, no en el entorno

- **Qué**: cada job hace `os.environ.setdefault("PYSPARK_PYTHON", sys.executable)`.
- **Alternativas**: exportar la variable en el perfil de PowerShell o en un
  script de arranque.
- **Por qué**: en Windows los workers de Python no heredan el venv y Spark
  muere con "Python worker failed to connect back". Fijarlo en código hace que
  el job funcione con solo invocar el intérprete correcto, sin ritual previo.
- **Coste**: dos líneas repetidas en cada entrypoint. Se centralizarán en un
  único helper de sesión de Spark en la Fase 2.

## D7 — El lenguaje del repo no está en los datos: la pregunta 1 se reformula

- **Qué**: la pregunta de negocio 1 pierde el corte por lenguaje del repo.
- **Alternativas**: enriquecer con la API de GitHub (5.000 req/h autenticado),
  o derivar un proxy desde las extensiones de fichero de los commits.
- **Por qué**: se comprobaron cuatro rutas candidatas en 770 `PullRequestEvent`
  y **ninguna existe**; el objeto `repo` solo trae `id`, `name` y `url`. La
  segunda opción mete una dependencia de red y de token que choca con "todo
  corre en Actions gratis"; la tercera es imposible, porque tampoco hay array
  de commits.
- **Coste**: el dashboard no podrá segmentar la actividad de bots por lenguaje.
  Se dice como limitación explícita en el README en lugar de disimularlo.

## D8 — La latencia de PR se deriva de los eventos, no de campos del payload

- **Qué**: los tiempos hasta primer review y hasta merge se calculan restando
  el `created_at` de eventos unidos por `payload.pull_request.id`.
- **Alternativas**: leer `created_at` / `merged_at` del propio PR, que es como
  estaba planteada la pregunta 2.
- **Por qué**: esos campos no existen en el payload recortado. El `id` del PR
  sí está al 100 % en los tres tipos de evento relevantes, y `payload.action`
  trae `merged` como valor propio, sin tener que inferirlo de `closed` + flag.
- **Coste**: amplifica la censura por los bordes de la ventana. Obliga a
  cohortar por fecha de apertura y a descartar explícitamente las cohortes sin
  madurar y los merges huérfanos, en vez de promediarlo todo.

## D9 — El entregable de la Fase 0 se separa en dos ficheros

- **Qué**: `analizar_hora.py` genera `docs/exploracion_datos.md` (tablas y
  ejemplos crudos); `docs/exploracion.md` lo escribo a mano con conclusiones.
- **Alternativas**: un único fichero generado, o uno único escrito a mano.
- **Por qué**: el anexo se regenera al analizar otra hora y machacaría
  cualquier análisis escrito encima; y las implicaciones sobre las preguntas de
  negocio no las puede redactar un script.
- **Coste**: hay que releer el anexo y actualizar las conclusiones a mano si se
  analiza otra hora. Es trabajo consciente, que es justo lo que se quiere aquí.

## D10 — La descarga se ejecuta en GitHub Actions, no en local

- **Qué**: la Fase 0 descarga y analiza en un runner de Actions, que publica el
  informe y el `.gz` como artefactos temporales.
- **Alternativas**: usar una VPN tipo Cloudflare WARP en local, o esperar a que
  el bloqueo remita.
- **Por qué**: `data.gharchive.org` resuelve a `188.114.96.5` / `.97.5`, y la
  conexión TCP al 443 no se establece desde esta red mientras que otros
  destinos sí. Verificado también desde una terminal limpia, sin proxy ni VPN
  configurados, así que el bloqueo es aguas arriba del router. El runner tiene salida limpia
  y el coste sigue siendo 0 € en un repo público.
- **Coste**: **no resuelve el backfill grande**, que debe correr en local por
  diseño. Si el bloqueo persiste, la Fase 1 se queda sin máquina donde correr y
  habrá que decidir entre VPN o replantear dónde vive el backfill.

---

## Revisión de D7 y D8 (2026-08-16)

Ambas se tomaron mirando **solo** una hora de 2026, y la comparación entre años
las deja obsoletas en parte. Se conservan porque el registro de decisiones es
un histórico, no un documento de estado.

- **D7 queda revocada.** El lenguaje del repo **sí existe** en
  `payload.pull_request.base.repo.language`, con ~90 % de cobertura estable
  entre 2016 y 2025-10-08. La pregunta 1 conserva el corte por lenguaje si la
  ventana se sitúa en el histórico rico. Lo que era cierto —y sigue siéndolo—
  es que en el formato posterior a 2025-10-09 no está.
- **D8 se mantiene, pero por otro motivo.** Los campos temporales sí existen en
  el histórico rico, así que la latencia se puede leer. Derivarla igualmente de
  los eventos deja de ser una necesidad y pasa a ser una elección: es la única
  vía que funciona en los dos formatos, y sirve de contraste contra los campos.

## D11 — Ventana histórica: 2024-10-09 → 2025-10-08

- **Qué**: un año de backfill que termina justo antes del cambio de formato.
- **Alternativas**: histórico más largo (varios años), o ventana reciente que
  incluya el formato nuevo.
- **Por qué**: es el tramo más largo con esquema homogéneo y payload completo
  que cabe en un año natural. Da cohortes de doce meses para la pregunta 3,
  lenguaje para la 1 y campos temporales para la 2, y esquiva tanto el tramo
  degradado como la frontera de formato.
- **Coste**: los datos terminan en octubre de 2025, así que el dashboard no
  será "actual" en su serie rica. El incremental diario aportará datos nuevos,
  pero con métricas limitadas y visualmente separados.

## D12 — El pipeline soporta los dos esquemas, detectados por campos

- **Qué**: bronze y silver aceptan el formato completo y el reducido, decidiendo
  por presencia de campos y no por fecha.
- **Alternativas**: soportar solo el formato rico y congelar el proyecto en
  octubre de 2025, o soportar solo el nuevo y renunciar al histórico.
- **Por qué**: la Fase 5 exige un cron diario, que necesariamente corre sobre
  el formato nuevo. Discriminar por fecha codificaría el 2025-10-09 en el
  código, y si la fuente vuelve a cambiar habría que tocarlo otra vez.
- **Coste**: el esquema de silver tendrá columnas nulas en el tramo reciente
  (lenguaje, latencias, conteo de commits), y los tests de calidad deben
  tolerarlo por tramo en vez de exigir cobertura uniforme.

## D13 — El tramo 2025-10-09 → 2025-10-14 se excluye como hueco conocido

- **Qué**: seis días marcados como no utilizables, no como días flojos.
- **Alternativas**: ingerirlos y dejar que el análisis los absorba.
- **Por qué**: traen entre 588 y 1.346 eventos por hora frente a los ~150.000
  esperados, un 0,4 %. No son datos escasos, son datos ausentes, y una serie
  temporal que los incluya muestra un desplome que no ocurrió en GitHub.
- **Coste**: hay que arrastrar una lista de huecos conocidos desde la ingesta
  hasta el dashboard. Queda fuera de la ventana de D11 de todos modos, pero el
  mecanismo hace falta igual para el incremental.

## D14 — La bisección del cambio de formato se hace en Actions

- **Qué**: `comparar_horas.py` más un workflow parametrizado por lista de
  fechas; cinco tandas para acotar el cambio de un rango de diez años a un día.
- **Alternativas**: descargar el histórico en local y comparar allí.
- **Por qué**: la red local no llega a GH Archive (D10), y el runner además
  paraleliza la descarga de varias fechas sin tocar la máquina del autor.
- **Coste**: cada iteración cuesta un ciclo de commit, push y espera. A cambio,
  el procedimiento queda registrado y es reproducible por cualquiera.

## D15 — D11 se confirma: un año de histórico rico cabe en disco

- **Qué**: se mantiene la ventana `2024-10-09 → 2025-10-08` del D11.
- **Alternativas**: acortarla a seis meses, o filtrar tipos de evento en bronze,
  que eran las dos salidas previstas si no cabía.
- **Por qué**: medido un día completo real (2025-08-13) son 2,012 GiB, que
  proyectan **~734 GiB al año** contra los 1.283 GiB libres de `D:`. Ocupa el
  57 % del disco, y el `.gz` se borra en cuanto la hora entra en bronze, así que
  el pico real es bastante menor que esa suma.
- **Coste**: el margen es cómodo pero no infinito, y obliga a que el borrado
  del crudo vaya al día en vez de acumularse hasta el final del backfill.

## D16 — Presupuesto de disco: 250 GB, fijado por el autor

- **Qué**: el proyecto no ocupa más de 250 GB (232,8 GiB) en total.
- **Alternativas**: usar los 1.378 GB libres de `D:`.
- **Por qué**: decisión del autor, que no quiere dedicar el disco entero a esto.
- **Coste**: **revoca D11 y D15**. Un año de histórico rico ya no cabe, y la
  ventana pasa a ser un problema de reparto de presupuesto en vez de una
  elección libre.

## D17 — Parquet con zstd en vez de snappy

- **Qué**: el códec de compresión de Parquet es zstd en todos los jobs.
- **Alternativas**: snappy, que es el que trae Spark por defecto.
- **Por qué**: medido sobre el mismo día, snappy da 3,599 GiB y zstd 1,723 GiB,
  un 52 % menos. **Con snappy el Parquet pesaba más que el `.gz` de origen**
  (1,788×), porque bronze guarda texto JSON, que es muy redundante. Y zstd
  además resultó **más rápido** (135 s frente a 223 s): hay tantos menos bytes
  que escribir que compensa de sobra el coste de CPU.
- **Coste**: zstd descomprime algo más lento que snappy en lecturas repetidas.
  Con este perfil —se escribe una vez y se lee por lotes— no compensa lo otro.

## D18 — Bronze proyecta el JSON íntegro solo en los tipos que lo necesitan

- **Qué**: las cinco columnas extraídas (`id`, `type`, `created_at`,
  `actor_login`, `repo_name`) se guardan para **todos** los eventos; el
  `evento_json` completo solo para `PullRequestEvent`,
  `PullRequestReviewEvent`, `PullRequestReviewCommentEvent`, `IssuesEvent` e
  `IssueCommentEvent`.
- **Alternativas**: guardar el JSON de todo (bronze puro), o descartar del todo
  los eventos que no sirven a las preguntas.
- **Por qué**: baja de 1,723 a 1,078 GiB por día (–37 %) y la duración del job a
  53 s. La clave es que la pregunta 3 solo necesita quién, dónde y cuándo, y eso
  vive en las columnas extraídas: **ningún evento se pierde**, se pierde el
  detalle de los que no lo usan. Descartar filas enteras sí habría roto la
  pregunta 3.
- **Coste**: si más adelante hiciera falta el payload de un tipo excluido —el
  array de commits de `PushEvent`, por ejemplo— hay que reingerir ese rango.
  Es el precio explícito de D16.

## D19 — Ventana en dos tramos, a un lado y otro del cambio de formato

Sustituye a D11.

- **Qué**:
  - **Tramo A, rico**: `2025-07-09 → 2025-10-08` (92 días, formato completo).
  - **Hueco**: `2025-10-09 → 2025-10-14` excluido por D13.
  - **Tramo B, actual**: `2025-10-15 → ayer` (~305 días, formato reducido),
    prolongado a diario por el cron de la Fase 5.
- **Alternativas**: un año limpio terminando en 2025-10-08 (el D11 original), o
  usar solo el formato nuevo.
- **Por qué**: el criterio es qué ve un reclutador al abrir el dashboard.
  - **Termina ayer, no hace diez meses.** Un dashboard cuyo último dato es de
    octubre de 2025 se lee como un proyecto abandonado, por muy buena que sea
    la razón técnica.
  - **Trece meses de cobertura** dan cohortes de retención con recorrido real.
    Con los tres meses que permitiría el presupuesto en formato rico, la
    pregunta 3 no tendría nada que enseñar.
  - **El cambio de formato pasa a ser el argumento**, no el estorbo: el
    dashboard muestra dos regímenes de datos y explica por qué, que es
    exactamente el tipo de problema que aparece en un trabajo real.
  - Las latencias de PR (D8) se derivan de los eventos, así que **funcionan en
    los dos tramos**: la pregunta 2 cubre los trece meses. Solo el corte por
    lenguaje queda limitado al tramo A.
- **Coste**: ~182 GiB de bronze más una provisión del 15 % para silver, unos
  209 GiB de los 232,8 disponibles. El margen es del 10 %, así que **la
  provisión de silver hay que sustituirla por una medición** en cuanto exista;
  si se pasa, el ajuste es recortar el tramo A, que es el caro.

## D19 bis — Enmienda por medición: el tramo A se amplía a 130 días

- **Qué**: el tramo A pasa de `2025-07-09 → 2025-10-08` (92 días) a
  **`2025-06-01 → 2025-10-08`** (130 días). El tramo B no cambia.
- **Por qué**: el tramo B se había estimado en 0,27 GiB/día escalando por el
  tamaño del `.gz`. Medido de verdad son **0,093 GiB/día**, un tercio, porque
  en el formato reducido los `PushEvent` no traen commits y la proyección de
  D18 los deja en nada. Eso libera unos 54 GiB del presupuesto.
- **Alternativas**: dejar el margen sin usar, o gastarlo en alargar el tramo B
  hacia atrás, que no aporta nada porque el tramo B ya llega hasta ayer.
- **Coste**: el margen baja del 10 % previsto a... en realidad sube al 17 %,
  porque la medición corrigió a la baja. Sigue dependiendo de que la provisión
  del 15 % para silver se confirme al medirlo.

## D20 — Los jobs limpian el staging huérfano de Spark al arrancar

- **Qué**: `bronze.py` borra los directorios `.spark-staging-*` del destino
  antes de escribir.
- **Alternativas**: confiar en que ningún job falle, o limpiar a mano de vez en
  cuando.
- **Por qué**: con `partitionOverwriteMode=dynamic`, Spark escribe en un
  temporal y lo promueve al final; si el job muere antes, el temporal se queda.
  Se detectó uno de **2,912 GiB** de un intento fallido, más del doble de lo que
  ocupaba la partición buena. En un backfill de 435 días esto son cientos de GiB
  de basura silenciosa, y con el presupuesto de D16 lo revienta sin avisar.
- **Coste**: si dos jobs corrieran a la vez sobre el mismo destino, uno borraría
  el staging del otro. El backfill es secuencial por diseño, así que no aplica,
  pero queda dicho por si algún día se paraleliza.

## D21 — Los actores se clasifican en cinco clases, no en un booleano

- **Qué**: `actor_clase` ∈ {`humano`, `agente_ia`, `bot_dependencias`,
  `bot_ci`, `bot_otro`}, en `spark_jobs/bots.py`. El sufijo `[bot]` decide si
  algo es automático; las listas solo deciden de qué tipo.
- **Alternativas**: un `is_bot` booleano, como decía el plan original.
- **Por qué**: la pregunta 1 pregunta por «bots **y agentes automáticos**», y
  meter `dependabot` y `devin-ai-integration` en el mismo cubo borra justo lo
  que se quiere medir. Lo que la lista no reconoce cae en `bot_otro`, nunca en
  `humano`: un falso negativo contamina la serie de humanos, que es la base de
  comparación.
- **Coste**: es una lista mantenida a mano y por tanto incompleta. Queda un
  **1,26 %** de eventos en `bot_otro`, y hay que decirlo en el dashboard en vez
  de presentar la clasificación como exhaustiva.

## D22 — La sesión de Spark fija `session.timeZone = UTC`

- **Qué**: todos los jobs fuerzan UTC.
- **Alternativas**: dejar la zona por defecto, que es la de la máquina.
- **Por qué**: `to_timestamp` interpretaba la `Z` de GH Archive y convertía a
  UTC+2, con lo que un día empezaba a las 02:00 y no a medianoche. Eso
  desplazaba las agregaciones diarias y contaminaba cualquier latencia. El dato
  es global; la zona de quien lo procesa no debe aparecer en él.
- **Coste**: ninguno de fondo. Sí obliga a recordar que **traer un timestamp a
  Python con `.first()` lo reconvierte a la zona del sistema operativo e ignora
  esta configuración**: por eso los tests formatean con `date_format` en Spark
  y comparan cadenas. El primer test acusó un desfase que solo existía en el
  propio test.

## D23 — Los tests vigilan la tasa de nulos, no exigen cero

- **Qué**: `repo` admite hasta un 0,01 % de nulos; `evento_id`, `tipo`,
  `creado_en`, `actor` y `actor_clase` siguen exigiendo cero.
- **Alternativas**: exigir cero en todas, o quitar `repo` de los tests.
- **Por qué**: apareció **un** `ForkEvent` sin `repo.name` **en el origen**,
  entre casi ocho millones. No es un fallo del pipeline y bloquear la promoción
  a gold por él sería un test que se ignora a la primera. El plan pide «tasa de
  nulos por columna», que es exactamente esto.
- **Coste**: un umbral es una decisión arbitraria. Se fija bajo a propósito
  (0,01 % son ~770 eventos al día) para que una degradación real siga saltando.

## D19 ter — Enmienda por medición: el tramo A baja a 116 días

- **Qué**: tramo A `2025-06-15 → 2025-10-08` (116 días), en lugar de 130.
- **Por qué**: silver ya no es una provisión. Medido son 43,2 GiB para los 435
  días, frente a los 25,3 que se habían provisionado al 15 %, sobre todo porque
  en el tramo B silver pesa casi lo mismo que bronze (96 %). Con 130 días el
  margen bajaba al 9 % sin contar gold ni el crudo transitorio.
- **Coste**: catorce días menos de histórico rico. La cobertura total queda en
  **14 meses** y el margen sube al 13 %, que ya absorbe gold y los picos.

## D19 quater — Tramo A a 55 días: el tramo B costaba cuatro veces más

- **Qué**: tramo A `2025-08-15 → 2025-10-08` (55 días). Tramo B sin cambios,
  `2025-10-15 → 2026-08-15` (305 días).
- **Por qué**: el coste del tramo B se había fijado midiendo **un solo día**
  (2026-08-12, 0,093 GiB). Muestreando un día de cada mes por `Content-Length`,
  la media real es 0,370 GiB/día: **113 GiB en vez de 28,4**. El volumen de GH
  Archive decrece de forma sostenida desde diciembre de 2025, y agosto de 2026
  era el punto más barato de la serie.
- **Alternativas**: recortar el tramo B por el principio, que además habría
  quitado los días más caros.
- **Por qué no esa**: el tramo B empieza justo después del hueco, y ese
  contraste inmediato con el tramo A es lo que hace legible el cambio de
  formato en el dashboard. Recortarlo por ahí ahorra disco y rompe el
  argumento.
- **Coste**: el histórico rico baja de 116 a 55 días. El lenguaje del repo y los
  campos temporales directos solo cubren mes y medio, y las latencias de PR
  sufren censura fuerte en ese tramo. Se compensa con que las latencias
  derivadas de eventos (D8) funcionan en los 12,5 meses completos.
- **Lección**: es la cuarta vez que una cifra estimada desde una sola muestra
  resulta estar mal. Ver la bitácora de la sesión 1, donde ya se anotó el mismo
  patrón.

## D24 — El scratch de Spark vive en `D:`, no en el temporal del sistema

- **Qué**: `spark.local.dir` apunta a `D:/gharchive-data/spark-tmp`.
- **Alternativas**: dejar el valor por defecto (`%TEMP%`, en `C:`).
- **Por qué**: `C:` tenía 90 GB libres y `D:` 1,2 TB. Un `dropDuplicates` sobre
  bronze completo generó **581 GiB en un solo `blockmgr`** y dejó el disco de
  sistema **en 0,5 GB libres**, con Windows al borde de fallar. Los datos viven
  en `D:`; el scratch que los procesa también debe.
- **Coste**: ninguno de fondo. Conviene vigilar `spark-tmp` porque los restos de
  un job muerto ya no se limpian solos al reiniciar como sí ocurre a veces en
  `%TEMP%`.

## D25 — La deduplicación va después de la proyección, nunca antes

- **Qué**: `dropDuplicates(["evento_id"])` se aplica dentro de cada constructor
  de silver, sobre columnas ya extraídas, en vez de sobre bronze entero.
- **Alternativas**: deduplicar una sola vez sobre bronze y reutilizarlo para
  las dos tablas, que era lo que hacía y parecía más eficiente.
- **Por qué**: deduplicar arrastra al shuffle **todas** las columnas, y en
  bronze eso incluye `evento_json`, el texto íntegro del evento y casi todo su
  peso. Barajar 149 GiB para quedarse con una decena de duplicados es el peor
  reparto de trabajo posible. Proyectando primero se barajan seis columnas
  cortas: el rango que agotaba el disco se resuelve en **112 s**.
- **Coste**: la deduplicación se ejecuta dos veces, una por tabla. Es
  irrelevante comparado con lo que ahorra, y es correcto porque cada tabla tiene
  su propio grano.

## D26 — Los tests concilian silver contra bronze, no solo su coherencia interna

- **Qué**: se añade una comprobación que compara, partición a partición, el
  número de filas de bronze con el de `silver/eventos`, y falla si alguna pierde
  más del 0,1 %.
- **Alternativas**: confiar en que un job que termina sin excepción ha escrito
  todo.
- **Por qué**: **las dieciséis comprobaciones anteriores pasaron en verde sobre
  un silver al que le faltaban 10.979.227 filas.** El job que lo escribió murió
  a mitad y dejó las 361 particiones creadas pero varias incompletas; como todos
  los tests miraban la coherencia interna de silver —unicidad, nulos, rangos,
  cobertura horaria—, ninguno podía detectar que faltara casi un 1 % de los
  datos. Un dataset truncado es internamente coherente.
- **Coste**: obliga a leer bronze entero en cada pasada de calidad, lo que
  encarece el test. Se hace con `count` por partición y no con `countDistinct`,
  que sobre 1.319 millones de filas tardaba más de diez minutos.
- **Umbral**: 0,1 %. Los duplicados reales medidos sobre el backfill completo
  son **12.364 de 1.319.395.759**, un 0,0009 %, así que el margen es amplio
  frente a la deduplicación legítima y sigue siendo estrecho frente a una
  pérdida real.

## D27 — `id` no es único globalmente: la deduplicación se acota al día

- **Qué**: `dropDuplicates(["evento_id", "event_date"])` en lugar de
  `dropDuplicates(["evento_id"])`. La clave de un evento es **el par (id,
  fecha)**, no el id solo.
- **Alternativas**: seguir deduplicando por id, que es lo que dice la
  especificación del proyecto («deduplicado por `id`») y lo que hace todo el
  mundo con GH Archive.
- **Por qué**: en el formato reducido **GH Archive reutiliza identificadores**.
  Se tomaron 200 ids que desaparecían del 2025-11-18 y los 200 reaparecían el
  2026-01-23 como eventos **distintos**: `PushEvent`, `CreateEvent` y
  `DeleteEvent` en noviembre; `IssuesEvent`, `PullRequestEvent` y `WatchEvent`
  en enero, con otro instante y otro actor. Deduplicar globalmente **borraba
  3.582.807 eventos reales**, no duplicados.
- **Cómo se vio**: la conciliación de D26 marcaba 287 días descuadrados. La
  pérdida estaba solo en el tramo B, solo en los tipos de mayor volumen y
  repartida uniformemente por hora — un patrón de filtro, no de truncamiento.
  El rango de `id` lo confirmó: en el tramo A es estrecho y creciente (53.449M
  → 53.467M en un día); en el tramo B es ancho y se solapa entre meses.
- **Coste**: dos consecuencias que hay que arrastrar.
  1. **`evento_id` no puede ser clave primaria en gold.** La clave del hecho es
     `(event_date, evento_id)`, y los tests de dbt de la Fase 3 deben declararse
     sobre el par, no sobre la columna sola.
  2. La deduplicación ya no protege contra un mismo evento republicado en dos
     días distintos. Medido: **cero casos** entre días consecutivos y entre
     días lejanos, así que el riesgo real es nulo con estos datos.

## D28 — Modelo en estrella: tres hechos, uno por pregunta de negocio

- **Qué**: `fct_pr_evento` (grano: evento de PR), `fct_pr_ciclo` (grano: un PR)
  y `fct_actividad_contribuyente` (grano: actor × repo × mes), sobre
  `dim_fecha`, `dim_actor` y `dim_repo`.
- **Alternativas**: un único hecho de eventos del que colgara todo, y dejar el
  cálculo de latencias y cohortes al dashboard.
- **Por qué**: cada pregunta tiene un grano distinto y mezclarlas obliga a
  reagrupar en cada consulta de Evidence, que es donde peor se depura. Con un
  hecho por pregunta, cada página del dashboard es un `select` casi directo.
- **Coste**: `fct_pr_evento` y `fct_pr_ciclo` comparten origen y se recalculan
  por separado. Es duplicación de cómputo, no de verdad: el grano manda.

## D29 — `dim_fecha` marca el formato de la fuente y los huecos

- **Qué**: la dimensión de fecha trae `formato_fuente`, `es_hueco_conocido` y
  `tiene_datos`.
- **Alternativas**: dejar esa información en la documentación y confiar en que
  quien haga el gráfico se acuerde.
- **Por qué**: el cambio de formato del 2025-10-09 y los seis días vacíos de
  D13 son propiedades **del dato**, no del proyecto. Teniéndolas en la
  dimensión, el dashboard puede sombrear el tramo o cortar la serie sin
  codificar fechas a mano en cada gráfico.
- **Coste**: la fecha del cambio queda escrita en el SQL de `dim_fecha`. Es el
  único sitio del pipeline donde aparece: silver la detecta por campos (D12).

## D30 — La censura se marca en el hecho, no se filtra

- **Qué**: `fct_pr_ciclo` expone `apertura_observada`, `merge_observado` y
  `cohorte_madura`, y conserva **todas** las filas.
- **Alternativas**: excluir de la tabla los PRs censurados.
- **Por qué**: el volumen de censura es en sí mismo un dato que hay que poder
  enseñar. Sobre la ventana de desarrollo, 440.260 PRs tenían apertura sin
  merge observado y 230.282 lo contrario: filtrarlos en silencio habría dado
  una media limpia y falsa.
- **Coste**: obliga a que cada consulta filtre. Está escrito en mayúsculas en
  la descripción del modelo, y es lo primero que hay que comprobar si un número
  de latencia parece demasiado bueno.

## D31 — Un test genérico propio en vez de `dbt_utils`

- **Qué**: `combinacion_unica`, doce líneas en `macros/`.
- **Alternativas**: añadir `dbt_utils` como dependencia.
- **Por qué**: hace falta porque **ninguna clave de los hechos es de una sola
  columna** (D27), y traer un paquete entero para un test no compensa en un
  proyecto que presume de no tener capas de más.
- **Coste**: si más adelante hacen falta tres o cuatro utilidades más, lo
  sensato será instalar el paquete y borrar esta macro.

## D32 — El estado de silver lo dice el disco, no el registro

- **Qué**: `silver_registro.jsonl` se reconstruyó desde las particiones
  existentes, contando filas con DuckDB sobre los footers de Parquet.
- **Alternativas**: fiarse del registro y reprocesar los 342 días que decía
  pendientes; o anotarlo solo en la bitácora sin tocar el registro.
- **Por qué**: el registro es un diario de lo que un proceso llegó a anotar, y
  se cortó cinco veces. Las 361 particiones estaban escritas y completas
  mientras el registro solo tenía 26 líneas: la reejecución iba a rehacer un
  año de datos ya hechos. La segunda alternativa deja la trampa armada.
- **Coste**: los días reconstruidos no tienen `segundos` medidos, y sin ese
  campo no se puede reconstruir a posteriori el coste del backfill de silver.

## D33 — `temp_directory` fuera de `settings` en el perfil de dbt

- **Qué**: se quitó `temp_directory` del bloque `settings` de `profiles.yml` y
  se dejó el valor por defecto de DuckDB (`<ruta_de_la_bd>.tmp`, que cae en
  `D:/gharchive-data/gold/`, el mismo disco del lago).
- **Alternativas**: bajar a `threads: 1` para que no se abran conexiones
  mientras otro modelo spillea; o mantener el ajuste y lanzar
  `fct_actividad_contribuyente` aislado del resto.
- **Por qué**: dbt-duckdb aplica `settings` con un `SET` en **cada conexión
  nueva**, y DuckDB responde `Cannot switch temporary directory after the
  current one has been used` en cuanto el directorio ya está en uso. Con 8
  threads los modelos que arrancan tarde fallan en el `BEGIN`, sin llegar a su
  SQL: es una carrera, no un fallo de esos modelos. Serializar a un thread
  esconde la carrera y multiplica el reloj de un `run` que ya es largo.
- **Coste**: el temporal deja de ser una ruta elegida y pasa a depender de
  dónde viva el `.duckdb`. Si algún día la base se mueve a un disco pequeño,
  el spill (54,70 GiB medidos en el intento de la sesión 3) se va con ella sin
  que nada lo avise.

## D34 — `memory_limit` de DuckDB a 24 GB y el temporal se queda en el disco del lago

- **Qué**: se sube `memory_limit` de 12 GB a 24 GB en `profiles.yml` y se
  mantiene el temporal en `D:/gharchive-data/gold/gh_archive.duckdb.tmp`.
- **Alternativas**: mover el temporal a otro disco (rechazada por Marcos); o
  dejar los 12 GB y serializar con `--threads 1` sin tocar la memoria.
- **Por qué**: con 12 GB y 8 threads, los cinco marts agregando 1.300 millones
  de filas a la vez generaron **594 GiB** de temporal creciendo a 1,71 GiB/min,
  y dejaron el disco del lago en 93 GiB libres: una hora escasa de margen. Más
  memoria es menos derrame, y como el lago y la base viven en `D:`, el derrame
  amenazaba a los datos, no solo al `run`. Los 12 GB protegían de una
  concurrencia con Spark que aquí no se da.
- **Coste**: si alguien lanza Spark y `dbt` a la vez, ahora se pelean por la
  RAM y lo probable es que muera Spark. El temporal sigue sin vigilancia en el
  mismo volumen que los datos: nada avisa antes de llenarlo.

## D35 — `silver_todo.py` verifica y anota por dia, no por lote

- **Qué**: la verificación tras escribir un lote pasa a contar filas partición
  a partición (`contar_por_dia`) y el registro recibe **una línea por día**,
  con `segundos_lote` y `dias_del_lote` en vez de un `segundos` que no era
  atribuible a ningún día.
- **Alternativas**: marcar el script como no reutilizable en Fase 5 y escribir
  otro para el incremental; o anotar una sola línea por lote con la fecha en
  formato rango.
- **Por qué**: con `--dias-por-lote` el código leía
  `event_date=2025-08-15..2025-08-21`, una carpeta que no existe porque las
  particiones son diarias. Cada lote habría escrito bien los datos y muerto en
  el `except` como FALLO sin anotar nada. Y aunque no hubiera fallado, anotar
  la fecha como rango rompe la reanudación, que compara contra días sueltos:
  el script daría por pendiente todo lo ya hecho en cada reejecución. La
  segunda alternativa deja ese fallo en pie.
- **Coste**: el camino del lote sigue **sin ejecutarse de verdad**. La prueba
  hecha solo cubre la reanudación (0 pendientes, sin arrancar Spark). Se
  validará con el primer día real de la Fase 5.

## D36 — Ventana recortada al 2026-03-14 para las tablas de PR

- **Qué**: `fct_pr_evento` y `fct_pr_ciclo` cortan en `fecha_pr_hasta`
  (2026-03-14). `fct_actividad_contribuyente` y las dimensiones mantienen el
  año completo. `cohorte_madura` pasa a medirse contra la fecha nueva.
- **Alternativas**: cortar todo el proyecto en marzo; publicar el año entero
  declarando la degradación con una banda en las gráficas; o no cortar.
- **Por qué**: desde el 2026-03-15 el feed de GH Archive deja de traer eventos
  que no sean `PushEvent`. La cuota de PR pasa del 12-14 % estable a no volver
  al 10 %, y en agosto es del 0,13 %. Está en bronze, o sea en el JSON crudo:
  es la fuente, no el pipeline. Publicar esa caída del 98 % en las preguntas 1
  y 2 mostraría un desplome de actividad que no ocurrió. Cortar todo el
  proyecto tira cinco meses de datos de contribuyentes que sí son buenos,
  porque los pushes siguen llegando. Declararlo con una banda es más fiel al
  dato, pero el criterio de exito del proyecto pide que un desconocido entienda
  el dashboard en diez segundos, y una gráfica que se desploma no se explica en
  diez segundos.
- **Coste**: las preguntas 1 y 2 pierden cinco meses y la ventana deja de
  llegar hasta hoy, lo que hay que explicar en el dashboard y en el README. El
  proyecto queda con dos ventanas distintas segun la pregunta, que es una
  asimetria que hay que documentar o confunde. Y la Fase 5, el cron diario,
  deja de tener sentido para las preguntas 1 y 2: cada dia nuevo cae en el
  tramo degradado.

## D37 — La pregunta 3 también se corta, y se corta en el exportador

- **Qué**: las consultas de P3 y la de `dim_fecha` en `exportar_gold.py` cortan
  en la misma ventana que D36. `fct_actividad_contribuyente` conserva el año
  entero en gold.
- **Alternativas**: dejar P3 con el año completo (lo que D36 hacía); o filtrar
  dentro del modelo y reconstruirlo.
- **Por qué**: D36 supuso que P3 aguantaba porque los pushes siguen llegando.
  Medido después, no aguanta: de marzo a julio se pierde el **25 % de actores
  distintos** mientras los eventos suben, que es la firma de que desaparece
  quien no hace push. Una curva de retención por cohortes mide justamente si
  alguien vuelve, así que ese 25 % se leería como fuga de contribuyentes. Se
  corta en el exportador y no en el modelo porque reconstruir ese mart son
  **7 h 17 min** para tirar filas que quizá interesen más adelante.
- **Coste**: gold y el dashboard dejan de tener la misma ventana, y eso solo se
  ve leyendo el exportador. Si alguien consulta el `.duckdb` directamente verá
  meses que el dashboard no muestra. Queda anotado aquí y en el comentario del
  fichero, pero es una trampa para el yo futuro.
