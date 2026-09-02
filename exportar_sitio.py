"""Exporta a JSON los datos de negocio que pinta el sitio estatico (site/).

Lee los MISMOS Parquet agregados que consume Evidence, en
dashboard/sources/gharchive/, y no el lago ni gold: asi el overview y el
dashboard ensenan el mismo numero por construccion, y este script corre en
segundos en cualquier maquina con el repo clonado.

Cada bloque lleva su `fuente` (el Parquet del que sale) para que cualquier
cifra del sitio sea rastreable hasta el fichero publicado.

Uso:
    python exportar_sitio.py
"""

import json
import sys
from datetime import date
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ / "dashboard" / "sources" / "gharchive"
DESTINO = RAIZ / "site" / "data" / "negocio.json"


def parquet(nombre: str) -> str:
    ruta = ORIGEN / f"{nombre}.parquet"
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta}. Ejecuta exportar_gold.py antes.")
    return f"read_parquet('{ruta.as_posix()}')"


def filas(con, sql: str) -> list[dict]:
    """Devuelve el resultado como lista de dicts con fechas en ISO."""
    cur = con.execute(sql)
    columnas = [d[0] for d in cur.description]
    salida = []
    for fila in cur.fetchall():
        registro = {}
        for col, val in zip(columnas, fila):
            if isinstance(val, date):
                val = val.isoformat()
            registro[col] = val
        salida.append(registro)
    return salida


def main() -> int:
    con = duckdb.connect()

    # ------------------------------------------------------------ ventana
    ventana = filas(con, f"""
        select min(fecha) as desde, max(fecha) as hasta, count(*) as dias,
               count(*) filter (where formato_fuente = 'completo') as dias_completos,
               count(*) filter (where es_hueco_conocido) as dias_hueco
        from {parquet('dim_fecha')}
    """)[0]

    # ------------------------------------------------------------ P1
    # Cuota mensual de eventos de PR que no son de humanos, y la de agentes
    # de IA aparte. Es el KPI de la pregunta 1.
    p1_mensual = filas(con, f"""
        select mes, actor_clase, eventos
        from {parquet('p1_actividad_mensual')}
        order by mes, actor_clase
    """)
    p1_cuota = filas(con, f"""
        select mes,
               sum(eventos) as eventos,
               round(100.0 * sum(eventos) filter (where actor_clase <> 'humano')
                     / sum(eventos), 1) as pct_no_humano,
               round(100.0 * sum(eventos) filter (where actor_clase = 'agente_ia')
                     / sum(eventos), 2) as pct_agente_ia
        from {parquet('p1_actividad_mensual')}
        group by mes order by mes
    """)
    p1_total = filas(con, f"""
        select sum(eventos) as eventos,
               round(100.0 * sum(eventos) filter (where actor_clase <> 'humano')
                     / sum(eventos), 1) as pct_no_humano
        from {parquet('p1_actividad_mensual')}
    """)[0]
    p1_agentes = filas(con, f"""
        select actor, sum(eventos) as eventos, max(repos) as repos
        from {parquet('p1_top_agentes')}
        group by actor order by eventos desc limit 10
    """)

    # ------------------------------------------------------------ P2
    # Solo cohortes maduras: es la unica poblacion sobre la que la latencia
    # no esta censurada por el borde de la ventana.
    p2_clases = filas(con, f"""
        select autor_clase, prs, con_review, con_merge_observable,
               mediana_min_review, mediana_min_merge, p90_h_merge
        from {parquet('p2_latencias_globales')}
        where cohorte_madura
        order by prs desc
    """)
    p2_mensual = filas(con, f"""
        select mes_apertura, autor_clase, mediana_min_review, mediana_min_merge
        from {parquet('p2_latencias_mensuales')}
        where cohorte_madura
        order by mes_apertura, autor_clase
    """)

    # ------------------------------------------------------------ P3
    p3_cohortes = filas(con, f"""
        select strftime(cohorte_mes, '%Y-%m') as cohorte, mes_de_vida, actores
        from {parquet('p3_retencion_cohortes')}
        order by cohorte_mes, mes_de_vida
    """)
    # Retencion al mes 1 y al mes 3 por cohorte: cuantos de los nuevos de un
    # mes vuelven a aparecer en el mismo repo uno y tres meses despues. Se
    # excluye la cohorte inicial, inflada por definicion (todo el que ya
    # estaba cuenta como nuevo en el primer mes de la ventana).
    p3_retencion = filas(con, f"""
        with base as (
            select cohorte_mes, mes_de_vida, actores
            from {parquet('p3_retencion_cohortes')}
        )
        select strftime(b0.cohorte_mes, '%Y-%m') as cohorte,
               b0.actores as nuevos,
               round(100.0 * b1.actores / b0.actores, 1) as pct_mes_1,
               round(100.0 * b3.actores / b0.actores, 1) as pct_mes_3
        from base b0
        left join base b1 on b1.cohorte_mes = b0.cohorte_mes and b1.mes_de_vida = 1
        left join base b3 on b3.cohorte_mes = b0.cohorte_mes and b3.mes_de_vida = 3
        where b0.mes_de_vida = 0
        order by b0.cohorte_mes
    """)
    p3_top_repos = filas(con, f"""
        select repo, sum(activos) as activos_acumulados, sum(nuevos) as nuevos_acumulados
        from {parquet('p3_repos_saldo')}
        group by repo order by activos_acumulados desc limit 10
    """)

    # ------------------------------------------------------------ fuente
    # Serie diaria de cuota de PushEvent y PullRequestEvent que escribe
    # degradacion.py sobre bronze. Se agrega a mes ponderando por eventos,
    # y se deja tambien la diaria: el corte del 2026-03-15 se ve mejor asi.
    degradacion = json.loads((RAIZ / "docs" / "degradacion_fuente.json").read_text(encoding="utf-8"))
    por_mes: dict[str, list[int]] = {}
    for dia in degradacion["serie"]:
        acum = por_mes.setdefault(dia["fecha"][:7], [0, 0, 0])
        acum[0] += dia["total"]; acum[1] += dia["push"]; acum[2] += dia["pr"]
    degradacion_mensual = [
        {"mes": mes, "eventos": t, "pct_push": round(100 * p / t, 1), "pct_pr": round(100 * pr / t, 2)}
        for mes, (t, p, pr) in sorted(por_mes.items())
    ]
    degradacion_diaria = [
        {"fecha": d["fecha"], "pct_pr": d["cuota_pr"], "pct_push": d["cuota_push"]}
        for d in degradacion["serie"]
    ]

    salida = {
        "generado": date.today().isoformat(),
        "degradacion": {
            "fuente": "docs/degradacion_fuente.json (degradacion.py sobre bronze)",
            "corte_pr": "2026-03-15",
            "mensual": degradacion_mensual,
            "diaria": degradacion_diaria,
        },
        "ventana": {"fuente": "dim_fecha.parquet", **ventana},
        "p1": {
            "fuente": "p1_actividad_mensual.parquet, p1_top_agentes.parquet",
            "total": p1_total,
            "cuota_mensual": p1_cuota,
            "mensual_por_clase": p1_mensual,
            "top_agentes": p1_agentes,
        },
        "p2": {
            "fuente": "p2_latencias_globales.parquet, p2_latencias_mensuales.parquet",
            "nota": "Cohortes maduras. Merge solo sobre PRs con merge observable (D38).",
            "por_clase": p2_clases,
            "mensual": p2_mensual,
        },
        "p3": {
            "fuente": "p3_retencion_cohortes.parquet, p3_repos_saldo.parquet",
            "nota": "Sin bots. La cohorte inicial (2025-08) esta inflada por la ventana.",
            "cohortes": p3_cohortes,
            "retencion": p3_retencion,
            "top_repos": p3_top_repos,
        },
    }

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    kb = DESTINO.stat().st_size / 1024
    print(f"Escrito {DESTINO} ({kb:.1f} KB)")
    print("Retencion por cohorte (mes 1 / mes 3):")
    for r in p3_retencion:
        print(f"  {r['cohorte']}  nuevos={r['nuevos']:>10,}  m1={r['pct_mes_1']}%  m3={r['pct_mes_3']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
