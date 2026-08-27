"""Cuando empieza la degradacion de la fuente: cuota de PushEvent por dia.

Los ficheros recientes de GH Archive son casi solo PushEvent. Esto localiza
la fecha de corte para decidir donde termina la ventana publicable.
Solo lectura.
"""
import duckdb, json
from pathlib import Path

con = duckdb.connect()
con.execute("set memory_limit='6GB'")
ruta = "D:/gharchive-data/silver/eventos/*/*.parquet"
filas = con.execute(f"""
    select event_date,
           count(*) total,
           count(*) filter (where tipo = 'PushEvent') push,
           count(*) filter (where tipo like 'PullRequest%') pr
    from read_parquet('{ruta}', hive_partitioning=true)
    group by 1 order by 1
""").fetchall()

serie = [{"fecha": str(f), "total": t, "push": p, "pr": r,
          "cuota_push": round(100 * p / t, 1), "cuota_pr": round(100 * r / t, 2)}
         for f, t, p, r in filas]

print(f"{'fecha':12} {'total':>10} {'%push':>7} {'%PR':>7}")
for x in serie:
    print(f"{x['fecha']:12} {x['total']:>10,} {x['cuota_push']:>7} {x['cuota_pr']:>7}")

# Primer dia a partir del cual la cuota de push no vuelve a bajar de 80
corte = None
for i, x in enumerate(serie):
    if x["cuota_push"] >= 80 and all(y["cuota_push"] >= 80 for y in serie[i:]):
        corte = x["fecha"]
        break
print(f"\nprimer dia con cuota de push >=80% de forma sostenida: {corte}")

Path("docs/degradacion_fuente.json").write_text(
    json.dumps({"corte": corte, "serie": serie}, indent=2), encoding="utf-8")
print("escrito docs/degradacion_fuente.json")
