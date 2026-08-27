"""Orquesta silver dia a dia, con registro y reanudacion.

Procesar silver de una tacada sobre 361 dias dura horas y, si se corta, se
pierde todo el avance. Aqui cada dia es una unidad independiente: se anota al
terminar, y una reejecucion salta lo ya hecho.

Trocear es correcto **porque la deduplicacion es por (evento_id, event_date)**
(D27). Con la deduplicacion global anterior el resultado dependia del tamano
del lote, que era justamente el error.

Uso:
    python silver_todo.py --desde 2025-08-13 --hasta 2026-08-15
    python silver_todo.py --desde 2025-08-13 --hasta 2026-08-15 --rehacer
"""

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "spark_jobs"))

from pyspark.sql import functions as F  # noqa: E402

from silver import construir_eventos, construir_pr_eventos  # noqa: E402
from sesion import crear_sesion, limpiar_staging, raiz_datos  # noqa: E402


def dias(desde: date, hasta: date):
    d = desde
    while d <= hasta:
        yield d.isoformat()
        d += timedelta(days=1)


def contar_por_dia(spark, directorio, dias):
    """Cuenta filas por particion diaria releyendo lo escrito.

    Devuelve {dia: filas}, omitiendo los dias que no tienen particion en
    disco. Lee solo las carpetas del lote y no el directorio entero, que a
    estas alturas son cientos de dias.
    """
    rutas = [str(directorio / f"event_date={d}") for d in dias
             if (directorio / f"event_date={d}").exists()]
    if not rutas:
        return {}
    filas = (spark.read.option("basePath", str(directorio)).parquet(*rutas)
             .groupBy("event_date").count().collect())
    return {str(r["event_date"]): r["count"] for r in filas}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", required=True)
    p.add_argument("--hasta", required=True)
    p.add_argument("--rehacer", action="store_true",
                   help="ignora el registro y reprocesa todo")
    p.add_argument("--dias-por-lote", type=int, default=7,
                   help="dias que se procesan en una sola pasada de Spark. "
                        "Agrupar reduce el coste de planificacion, que se "
                        "pagaba 361 veces yendo dia a dia; a cambio, un corte "
                        "cuesta el lote entero. Es seguro agrupar porque la "
                        "deduplicacion es intra-dia (D27).")
    args = p.parse_args()

    raiz = Path(raiz_datos())
    registro = raiz / "silver_registro.jsonl"

    hechos = set()
    if registro.exists() and not args.rehacer:
        for linea in registro.read_text(encoding="utf-8").splitlines():
            try:
                hechos.add(json.loads(linea)["fecha"])
            except Exception:
                pass

    lista = list(dias(date.fromisoformat(args.desde), date.fromisoformat(args.hasta)))
    pendientes = [f for f in lista if f not in hechos]
    print(f"{len(lista)} dias en el rango, {len(hechos)} ya hechos, "
          f"{len(pendientes)} pendientes", flush=True)
    if not pendientes:
        return 0

    spark = crear_sesion("silver-todo")
    bronze_todo = spark.read.parquet(str(raiz / "bronze"))
    inicio = time.monotonic()
    ok = fallos = 0

    # Bronze no cubre todos los dias del rango: el tramo A empieza el
    # 2025-08-15 y el hueco de D13 no existe. Se descartan antes de agrupar.
    con_bronze = [f for f in pendientes
                  if (raiz / "bronze" / f"event_date={f}").exists()]
    saltados = len(pendientes) - len(con_bronze)
    if saltados:
        print(f"{saltados} dias del rango no estan en bronze, se saltan",
              flush=True)

    n = args.dias_por_lote
    lotes = [con_bronze[k:k + n] for k in range(0, len(con_bronze), n)]
    print(f"{len(lotes)} lotes de hasta {n} dias", flush=True)

    for i, lote in enumerate(lotes, 1):
        fecha = f"{lote[0]}..{lote[-1]}"
        try:
            b = bronze_todo.filter(F.col("event_date").isin(lote))
            t0 = time.monotonic()

            d_ev = raiz / "silver" / "eventos"
            d_pr = raiz / "silver" / "pr_eventos"
            limpiar_staging(d_ev)
            limpiar_staging(d_pr)

            (construir_eventos(b).write.mode("overwrite")
                .partitionBy("event_date").parquet(str(d_ev)))
            (construir_pr_eventos(b).write.mode("overwrite")
                .partitionBy("event_date").parquet(str(d_pr)))

            # Se cuenta releyendo las particiones: confirma que lo escrito
            # es legible, no solo que el write no lanzo excepcion. Se cuenta
            # por dia, no por lote: las particiones son diarias y
            # "2025-08-15..2025-08-21" no es ninguna carpeta.
            por_dia_ev = contar_por_dia(spark, d_ev, lote)
            por_dia_pr = contar_por_dia(spark, d_pr, lote)

            sin_particion = [f for f in lote if f not in por_dia_ev]
            if sin_particion:
                raise RuntimeError("sin particion en silver/eventos: "
                                   + ", ".join(sin_particion))

            segundos = round(time.monotonic() - t0, 1)
            # Una linea por dia, no por lote: el registro se consulta por dia
            # y asi sigue valiendo aunque el lote cambie de tamano. Los
            # segundos son los del lote entero y van marcados como tales.
            with registro.open("a", encoding="utf-8") as f:
                for dia in lote:
                    f.write(json.dumps({
                        "fecha": dia,
                        "eventos": por_dia_ev[dia],
                        "pr_eventos": por_dia_pr.get(dia, 0),
                        "segundos_lote": segundos,
                        "dias_del_lote": len(lote),
                    }) + "\n")
            ok += 1

            n_ev = sum(por_dia_ev.values())
            n_pr = sum(por_dia_pr.values())

            ritmo = (time.monotonic() - inicio) / ok
            faltan = (len(lotes) - i) * ritmo
            print(f"[{i}/{len(lotes)}] {fecha}: "
                  f"eventos={n_ev:,} pr={n_pr:,} {segundos}s "
                  f"| faltan ~{faltan/60:.0f} min", flush=True)

        except Exception as exc:
            fallos += 1
            print(f"[{i}/{len(lotes)}] {fecha} FALLO: "
                  f"{type(exc).__name__}: {exc}", flush=True)

    spark.stop()
    print(f"\nTerminado en {(time.monotonic()-inicio)/60:.1f} min. "
          f"ok={ok} fallos={fallos}", flush=True)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
