-- PREGUNTA DE NEGOCIO 1: que parte de la actividad de PRs la generan bots y
-- agentes automaticos, y como evoluciona en el tiempo.
--
-- GRANO: un evento relacionado con un pull request.
-- CLAVE: (fecha, evento_id). No evento_id solo: en el formato reducido GH
--        Archive reutiliza identificadores entre fechas distintas (D27).

{{ config(materialized='table') }}

select
    e.fecha,
    e.evento_id,
    e.creado_en,
    e.tipo,
    e.accion,
    e.es_merge,
    e.esquema,

    e.actor,
    e.actor_clase,
    e.actor_es_bot,

    e.repo,
    e.repo_lenguaje,

    e.pr_id,
    e.pr_numero,
    e.pr_lineas_add,
    e.pr_lineas_del,
    e.review_estado
from {{ ref('stg_pr_eventos') }} e
-- La serie termina el 2026-03-14: despues, la fuente deja de publicar
-- eventos de PR y la caida del 98% que se veria en el grafico seria un
-- artefacto, no actividad real. Ver D36.
where e.fecha <= date '{{ var("fecha_pr_hasta") }}'
