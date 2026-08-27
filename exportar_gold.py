"""Exporta agregados de gold a Parquet, para que el dashboard los lea.

Evidence construye en un runner de Actions que NO tiene acceso al lago: bronze
y silver son cientos de GiB y viven en la maquina del autor. Lo que sube al
repo son estas tablas, ya agregadas, que pesan MB.

Cada consulta responde a una pregunta de negocio concreta. Si un agregado no
sirve a ninguna de las tres, no entra: es la regla del proyecto.

Uso:
    python exportar_gold.py
"""

import os
import sys
from pathlib import Path

import duckdb

DESTINO = Path(__file__).resolve().parent / "dashboard" / "sources" / "gharchive"

# Tope de seguridad: si un agregado se dispara, es que su grano esta mal
# elegido y no debe acabar en el repo por accidente.
MAX_MB_POR_FICHERO = 40

# Fin de la ventana publicable. A partir del 2026-03-15 el feed de GH Archive
# deja de traer eventos que no sean PushEvent (D36). Para las preguntas 1 y 2
# el corte ya esta hecho en los propios modelos; la pregunta 3 se corta aqui,
# porque su mart conserva el ano entero a proposito y no compensa reconstruirlo
# 7 h para tirar filas. Medido: de marzo a julio se pierde el 25% de actores
# distintos mientras los eventos suben, la firma de que desaparece quien no
# hace push. Una cohorte de retencion sobre eso mostraria una fuga que no
# ocurrio. El corte va escrito en cada consulta de P3 como literal
# (2026-03-01, ultimo mes completo bueno), no como constante interpolada: las
# consultas son cadenas planas y un .format() rompería cualquiera que llevase
# llaves. Ver D37.


CONSULTAS = {
    # ---------------------------------------------------------------- P1
    "p1_actividad_mensual": """
        select
            date_trunc('month', fecha)::date as mes,
            actor_clase,
            count(*)                          as eventos,
            count(distinct repo)              as repos,
            count(distinct actor)             as actores
        from fct_pr_evento
        group by 1, 2
        order by 1, 2
    """,
    "p1_por_lenguaje": """
        select
            date_trunc('month', fecha)::date as mes,
            repo_lenguaje                     as lenguaje,
            actor_clase,
            count(*)                          as eventos
        from fct_pr_evento
        where repo_lenguaje is not null
        group by 1, 2, 3
        having count(*) >= 50
        order by 1, 4 desc
    """,
    "p1_top_agentes": """
        select
            date_trunc('month', fecha)::date as mes,
            actor,
            count(*)                          as eventos,
            count(distinct repo)              as repos
        from fct_pr_evento
        where actor_clase = 'agente_ia'
        group by 1, 2
        order by 1, 3 desc
    """,

    # ---------------------------------------------------------------- P2
    # cohorte_madura sale como COLUMNA, no como filtro: si se filtrara aqui,
    # una ventana sin cohortes maduras produciria una tabla vacia y el
    # dashboard no podria ni explicar por que no hay datos. Filtrar es tarea
    # de la pagina, que ademas asi puede ensenar cuanto se descarta.
    "p2_latencias_mensuales": """
        select
            date_trunc('month', abierto_en)::date as mes_apertura,
            autor_clase,
            cohorte_madura,
            count(*)                                as prs,
            count(horas_hasta_primer_review)        as con_review,
            count(horas_hasta_merge)                as con_merge,
            -- En minutos, no en horas: las medianas de merge estan por
            -- debajo de los dos minutos y en horas con dos decimales salen
            -- como 0.00, que en el grafico se lee como "sin dato" en vez de
            -- como "instantaneo". El p90 si va en horas porque ahi la escala
            -- es de dias.
            round(median(horas_hasta_primer_review) * 60, 1) as mediana_min_review,
            round(median(horas_hasta_merge) * 60, 1)         as mediana_min_merge,
            round(quantile_cont(horas_hasta_merge, 0.9), 2)  as p90_h_merge
        from fct_pr_ciclo
        where apertura_observada
          and autor_clase is not null
        group by 1, 2, 3
        order by 1, 2
    """,
    "p2_censura": """
        select
            date_trunc('month', primera_fecha)::date as mes,
            apertura_observada,
            merge_observado,
            count(*) as prs
        from fct_pr_ciclo
        group by 1, 2, 3
        order by 1
    """,

    # ---------------------------------------------------------------- P3
    "p3_retencion_cohortes": """
        select
            cohorte_mes,
            mes_de_vida,
            count(distinct actor)                    as actores,
            count(distinct repo)                     as repos
        from fct_actividad_contribuyente
        where not es_bot
          and mes <= date '2026-03-01'
        group by 1, 2
        order by 1, 2
    """,
    "p3_repos_saldo": """
        with por_mes as (
            select repo, mes,
                   count(distinct actor) filter (where es_primer_mes) as nuevos,
                   count(distinct actor)                              as activos
            from fct_actividad_contribuyente
            where not es_bot
              and mes <= date '2026-03-01'
            group by 1, 2
        )
        select repo, mes, nuevos, activos
        from por_mes
        where activos >= 5
        order by mes, activos desc
    """,

    # ---------------------------------------------------- contexto / avisos
    "dim_fecha": """
        select fecha, anio, mes, formato_fuente, es_hueco_conocido, tiene_datos
        from dim_fecha
        where fecha <= date '2026-03-14'
        order by fecha
    """,
}


def main() -> int:
    raiz = os.environ.get("GHA_DATA_DIR", "D:/gharchive-data")
    bd = Path(raiz) / "gold" / "gh_archive.duckdb"
    if not bd.exists():
        print(f"No existe {bd}. Ejecuta dbt run antes.")
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(bd), read_only=True)

    total = 0
    problemas = []
    for nombre, sql in CONSULTAS.items():
        salida = DESTINO / f"{nombre}.parquet"
        con.execute(
            f"copy ({sql}) to '{salida.as_posix()}' (format parquet, compression zstd)")
        mb = salida.stat().st_size / 1024 ** 2
        filas = con.sql(f"select count(*) from read_parquet('{salida.as_posix()}')").fetchone()[0]
        total += mb
        marca = ""
        if mb > MAX_MB_POR_FICHERO:
            marca = "  <-- DEMASIADO GRANDE"
            problemas.append(nombre)
        print(f"  {nombre:26} {filas:>10,} filas  {mb:7.2f} MB{marca}")

    con.close()
    print(f"\nTotal exportado: {total:.2f} MB en {DESTINO}")
    if problemas:
        print(f"\nRevisa el grano de: {', '.join(problemas)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
