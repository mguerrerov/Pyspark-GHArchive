# Sesión 5 — 2026-09-02

Sesión de cierre del dashboard y de apertura del artefacto público definitivo.
Se cerraron las cuatro decisiones que la sesión 4 dejó abiertas, se descubrió
que el dashboard llevaba tres despliegues publicado **roto**, y se construyó el
sitio estático del proyecto en Netlify: portada con las respuestas y página de
BI del propio pipeline.

## Qué se hizo

**Se cerraron las cuatro decisiones pendientes** (commit `f4aac46`):

- D39 estaba a medias: `p2_latencias_globales` existía pero le faltaba el
  `.sql` de la fuente, así que Evidence no encontraba la tabla.
- **D40** · la página de latencias no colapsa las clases automáticas, y lo dice
  con las cifras: `bot_ci` 0,1 min, `bot_dependencias` 184,4 min, humano 1,8.
- **D41** · `p3_repos_saldo` recortado a los 2.000 repos más activos con el
  grano mensual intacto: de 15,09 MB a 78,6 KB. El export entero pasa de 15,11
  MB a 0,09 MB (factor 168). Tope del exportador bajado a 5 MB.
- **D42** · la Fase 5 automatiza la ingesta y el detector de degradación, no la
  publicación: cada día nuevo cae en el tramo degradado.

**Se cuadró `metrics.md`.** La tabla de "mediana real del periodo" tenía 1,9
min y 26,7 h de p90 para humanos; el Parquet publicado dice 1,8 y 24,63. La
población coincidía exactamente; lo que difería era el filtro de merge. Las
cifras salen ahora del fichero que sube al repo. La medición agregada
bot/humano de agosto quedó marcada como superada.

**Se descubrió que el dashboard publicado se servía sin CSS ni JS** desde el
primer despliegue de la Fase 4, con tres runs de Pages en verde. Causa:
`EVIDENCE_BASE_PATH` en el entorno del workflow **no hace nada**; Evidence 40
lee `deployment.basePath` de `evidence.config.yaml` y de ningún otro sitio
(comprobado en `node_modules/@evidence-dev/sdk`). Arreglado en `8b83e5f`.

**Se construyó el sitio público en Netlify** (`4a8ef74` y siguientes):

- `site/`: `index.html` (problema, cómo se hizo, las tres respuestas con KPI y
  gráfico, conclusiones, límites de la fuente) y `metricas.html` (volumen,
  disco, tiempos, calidad, fuente, incidentes, ficha). HTML a mano, Tailwind
  v4 por CLI, ECharts. Sin framework.
- `exportar_sitio.py` lee los nueve Parquet publicados y escribe
  `site/data/negocio.json`; `pipeline.json` va a mano con la línea de
  `metrics.md` de cada cifra, y `comprobar_sitio.py` verifica que el valor está
  en esa línea: 89 entradas, 59 valores, 0 fallos.
- `construir_sitio.sh` construye Evidence con `basePath: /dashboard`, compila
  Tailwind y ensambla `dist/`. Es el mismo script en local y en `netlify.toml`.
- Netlify: proyecto `pyspark-gharchive` creado por CLI, desplegado desde
  `dist/` local. **https://pyspark-gharchive.netlify.app**. GitHub Pages
  retirado (`pages.yml` eliminado).
- La home de Evidence redirige a la portada del proyecto (301 en
  `netlify.toml`); el antiguo `index.md` del dashboard pasa a `datos.md`.
- El gráfico de cohortes de `retencion.md` salía vacío con la cohorte como
  `DATE`; va como texto y en porcentaje de la cohorte, no en actores.

**Cifras nuevas medidas**: retención por cohorte (15-19 % vuelven al mes
siguiente, 5-7,5 % siguen a los tres meses, sin contar la cohorte inflada de
agosto); 42,0 % de los 80,6 M de eventos de PR de la ventana no son humanos.

## Decisiones tomadas

- **D40, D41, D42** (arriba).
- **D43** · sitio estático aparte en Netlify, Evidence bajo `/dashboard`, un
  solo build. Pages fuera.
- **D44** · los JSON del sitio se generan en local y se commitean, como los
  Parquet. Netlify no tiene el lago ni Python.
- Marcos anuló para este sitio la regla del CLAUDE.md de que las conclusiones
  las escribe él: las redactó Claude, con las cifras al lado.

## Errores cometidos, y cómo se resolvieron

1. **Un build en verde no es un sitio que funciona.** Tres despliegues de Pages
   en verde con la página sin estilos. `evidence build` no comprueba que los
   assets resuelvan en el dominio destino. → Abrir la página es parte de la
   verificación, siempre. Lo mismo con el LineChart de cohortes: vacío en
   producción, sin ningún error en el build.
2. **Se supuso que una variable de entorno con nombre plausible haría algo.**
   `EVIDENCE_BASE_PATH` no existe en Evidence 40. → Se buscó en el código del
   paquete de dónde sale el `basePath` antes de tocar nada más.
3. **La skill de Tailwind que pidió Marcos** (`timelessco/recollect`) no
   existe. → Se usó la que pasó después (`blencorp/claude-code-kit`), guardada
   en `~/.claude/skills/tailwindcss/`.
4. **Chrome no llega a `localhost`** desde la extensión (permiso por sitio). →
   La verificación visual se hizo sobre Netlify una vez público. Antes, un smoke
   test en Node comprobó que los 14 constructores de gráfico devolvían series
   con datos.
5. **Netlify crea los sitios privados por defecto** ("Private by default",
   novedad de 2026) y no hay campo en la API para cambiarlo. → Marcos lo puso
   público desde el panel.
6. **Un enlace `(/)` en una página de Evidence** se convierte en `/dashboard/`
   por el `basePath` y habría entrado en bucle con la redirección. → URL
   absoluta.
7. **`es-ES` no agrupa los números de cuatro cifras** ("1319" en vez de
   "1.319"). → `Intl.NumberFormat('de-DE')`, que usa los mismos separadores.

## Estado

| Pieza | Estado |
|---|---|
| bronze / silver / gold | sin cambios; completos y verificados (sesión 4) |
| agregados | 9 Parquet, 0,09 MB, ventana 2025-08-13 → 2026-03-14 |
| dashboard Evidence | en **https://pyspark-gharchive.netlify.app/dashboard/bots/** (la raíz de `/dashboard/` redirige a la portada) |
| sitio estático | **https://pyspark-gharchive.netlify.app**, público, revisado en Chrome |
| GitHub Pages | desactivado por Marcos el 2026-09-03; github.io devuelve 404 |

## Qué queda pendiente y por dónde se retoma

**Repo conectado en Netlify el 2026-09-03** por Marcos desde el panel (la
CLI pedía OAuth de GitHub interactivo). El primer build desde Git terminó en
verde en 69 s; desde ahora cada push a `main` despliega solo.

**Power BI descartado y README escrito** (D45, 2026-09-03): la BI vive en el
sitio, y Marcos pidio que el README lo redactara Claude.

**La Fase 5 no se hace**, decidido por Marcos el 2026-09-03: el README la
explica como decisión (D42), no como pendiente. Si la fuente se recupera, lo
primero sería un cron que corra `degradacion.py` sobre el día nuevo.

**Punto exacto de retome: no queda nada estructural.** El proyecto está
entregado: sitio público, dashboard, README, decisiones y métricas al día.

1. Cosmético: los KPI del hero envuelven en pantallas estrechas; el título
   "Sobre Los Datos" del menú de Evidence sale en Title Case por el propio
   Evidence.

## Servicios al cerrar

- Servidor local `http.server` en el 8765: **parado** (TaskStop).
- Sesiones de Spark, dbt, DuckDB: ninguna se lanzó en esta sesión.
- Pestañas de Chrome de la sesión: cerradas.
- `dist/` y `site/assets/app.css` quedan en disco, ignorados por git.
- Sin descargas ni procesos en segundo plano.
