-- PREGUNTA DE NEGOCIO 2: cuanto tarda un PR en recibir su primer review y en
-- mergearse, y si difiere entre PRs de bot y de humano.
--
-- GRANO: un pull request.
-- CLAVE: (repo, pr_id). Se incluye repo por precaucion: GH Archive reutiliza
--        identificadores en el formato reducido (D27), y aunque no se ha
--        observado reutilizacion de pr_id, la clave compuesta lo hace
--        irrelevante.
--
-- Las latencias se derivan de los instantes de los EVENTOS, no de campos del
-- payload (D8): es la unica via que funciona en los dos formatos, y mide
-- cuando GitHub emitio el hecho.
--
-- CENSURA: un PR abierto antes del inicio de la ventana no tiene evento de
-- apertura observable, y uno abierto al final puede no haberse mergeado aun.
-- Ambos casos se marcan y NO deben promediarse sin filtrar por
-- `apertura_observada` y `cohorte_madura`.

{{ config(materialized='table') }}

with eventos as (
    -- Ventana recortada: ver D36. Despues del 2026-03-14 la fuente deja de
    -- publicar eventos de PR, y un PR abierto cerca de ese limite tendria su
    -- ciclo cortado por la degradacion y no por el comportamiento real.
    select * from {{ ref('stg_pr_eventos') }}
    where fecha <= date '{{ var("fecha_pr_hasta") }}'
),

agregado as (
    select
        repo,
        pr_id,

        min(case when accion = 'opened' then creado_en end)  as abierto_en,
        min(case when tipo = 'PullRequestReviewEvent'
                 then creado_en end)                          as primer_review_en,
        min(case when es_merge then creado_en end)            as mergeado_en,
        max(case when accion = 'closed' and not es_merge
                 then creado_en end)                          as cerrado_sin_merge_en,

        -- El autor del PR es quien lo abrio; si no se observo la apertura, se
        -- deja nulo en vez de inventar uno a partir de otro evento.
        min(case when accion = 'opened' then actor end)       as autor,
        min(case when accion = 'opened' then actor_clase end) as autor_clase,

        max(repo_lenguaje)                                    as lenguaje,
        max(esquema)                                          as esquema,
        count(*)                                              as eventos_del_pr,
        count(distinct case when tipo = 'PullRequestReviewEvent'
                            then evento_id end)               as reviews,
        min(fecha)                                            as primera_fecha,
        max(fecha)                                            as ultima_fecha
    from eventos
    group by repo, pr_id
)

select
    repo,
    pr_id,
    autor,
    autor_clase,
    lenguaje,
    esquema,
    abierto_en,
    primer_review_en,
    mergeado_en,
    cerrado_sin_merge_en,
    reviews,
    eventos_del_pr,
    primera_fecha,
    ultima_fecha,

    date_trunc('month', abierto_en)::date as cohorte_apertura,

    -- Banderas de censura. Sin ellas, cualquier media sale sesgada.
    abierto_en is not null                as apertura_observada,
    mergeado_en is not null               as merge_observado,

    -- Una cohorte esta madura si han pasado 30 dias desde su apertura dentro
    -- de la ventana: por debajo de eso, los PRs lentos aun no han podido
    -- mergearse y la media se sesga a la baja.
    abierto_en is not null
        and abierto_en <= date '{{ var("fecha_pr_hasta") }}' - interval 30 day
                                          as cohorte_madura,

    -- En segundos, no en minutos: date_diff cuenta cruces de frontera, asi
    -- que con 'minute' cualquier latencia por debajo del minuto vale 0. Medido
    -- el 2026-08-27, eso ponia la mediana de merge en 0,00 h tanto para bots
    -- como para humanos y borraba la respuesta a la pregunta 2; con segundos
    -- son 5 s y 101 s. Ver metrics.md.
    case when abierto_en is not null and primer_review_en is not null
              and primer_review_en >= abierto_en
         then date_diff('second', abierto_en, primer_review_en) / 3600.0
    end                                   as horas_hasta_primer_review,

    case when abierto_en is not null and mergeado_en is not null
              and mergeado_en >= abierto_en
         then date_diff('second', abierto_en, mergeado_en) / 3600.0
    end                                   as horas_hasta_merge
from agregado
