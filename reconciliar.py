"""Reconciliacion bronze<->silver por dia (D26).

Cuenta filas por particion en las dos capas y lista los dias donde no
coinciden. Solo lectura: no toca ningun dato.
"""
import duckdb, json, sys
from pathlib import Path

raiz = Path("D:/gharchive-data")
con = duckdb.connect()
con.execute("set memory_limit='6GB'")


def por_dia(capa, distintos=False):
    """Filas por dia. Con distintos=True cuenta ids unicos en vez de filas.

    Bronze se cuenta por ids distintos porque silver deduplica por
    (evento_id, event_date) por diseno (D9). Comparar filas contra filas da
    un descuadre falso igual al numero de duplicados de bronze: medido el
    2026-08-26, 12.364 en 194 dias, que coinciden al digito con los
    duplicados reales.
    """
    ruta = str(raiz / capa / "*" / "*.parquet")
    cuenta = "count(distinct id)" if distintos else "count(*)"
    q = f"""select event_date, {cuenta} n
            from read_parquet('{ruta}', hive_partitioning=true)
            group by 1"""
    return {str(r[0]): r[1] for r in con.execute(q).fetchall()}


b = por_dia("bronze", distintos=True)
e = por_dia("silver/eventos")
print(f"bronze (ids distintos): {len(b)} dias, {sum(b.values()):,} filas", flush=True)
print(f"silver/eventos: {len(e)} dias, {sum(e.values()):,} filas", flush=True)

desc = []
for d in sorted(b):
    if b[d] != e.get(d, 0):
        desc.append({"fecha": d, "bronze": b[d], "silver": e.get(d, 0),
                     "faltan": b[d] - e.get(d, 0)})

print(f"\ndias descuadrados: {len(desc)} de {len(b)}")
print(f"filas que faltan en total: {sum(x['faltan'] for x in desc):,}")
for x in desc[:40]:
    print(f"  {x['fecha']}  bronze={x['bronze']:>9,}  silver={x['silver']:>9,}  faltan={x['faltan']:>8,}")
if len(desc) > 40:
    print(f"  ... y {len(desc)-40} mas")

Path("docs/reconciliacion.json").write_text(
    json.dumps(desc, indent=2), encoding="utf-8")
print("\nescrito docs/reconciliacion.json")
