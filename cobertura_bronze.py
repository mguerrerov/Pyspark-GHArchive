"""Cobertura horaria de bronze (Fase 2).

GH Archive publica un fichero por hora. Un dia completo tiene 24 horas
presentes. Esto cuenta horas distintas por dia y las filas de cada hora, para
distinguir "falta la hora entera" de "la hora esta pero venia corta".

Solo lectura.
"""
import duckdb, json
from pathlib import Path

raiz = Path("D:/gharchive-data")
con = duckdb.connect()
con.execute("set memory_limit='6GB'")

ruta = str(raiz / "bronze" / "*" / "*.parquet")
q = f"""
select event_date,
       cast(substr(created_at, 12, 2) as int) as hora,
       count(*) as n
from read_parquet('{ruta}', hive_partitioning=true)
group by 1, 2
"""
filas = con.execute(q).fetchall()
print(f"{len(filas):,} pares (dia, hora) leidos", flush=True)

por_dia = {}
for fecha, hora, n in filas:
    por_dia.setdefault(str(fecha), {})[hora] = n

incompletos = []
for d in sorted(por_dia):
    horas = por_dia[d]
    faltan = [h for h in range(24) if h not in horas]
    if faltan:
        incompletos.append({"fecha": d, "horas_presentes": len(horas),
                            "horas_ausentes": faltan})

print(f"\ndias en bronze: {len(por_dia)}")
print(f"dias sin las 24 horas: {len(incompletos)}")
for x in incompletos[:40]:
    print(f"  {x['fecha']}  {x['horas_presentes']}/24  faltan {x['horas_ausentes']}")
if len(incompletos) > 40:
    print(f"  ... y {len(incompletos)-40} mas")

# Horas anormalmente cortas: menos de un tercio de la mediana de su dia.
cortas = []
for d in sorted(por_dia):
    vals = sorted(por_dia[d].values())
    med = vals[len(vals) // 2]
    for h, n in sorted(por_dia[d].items()):
        if n < med / 3:
            cortas.append({"fecha": d, "hora": h, "filas": n, "mediana_dia": med})

print(f"\nhoras presentes pero anormalmente cortas: {len(cortas)}")
for x in cortas[:25]:
    print(f"  {x['fecha']} h{x['hora']:02d}  {x['filas']:,} filas (mediana del dia {x['mediana_dia']:,})")
if len(cortas) > 25:
    print(f"  ... y {len(cortas)-25} mas")

Path("docs/cobertura_bronze.json").write_text(
    json.dumps({"dias_incompletos": incompletos, "horas_cortas": cortas},
               indent=2), encoding="utf-8")
print("\nescrito docs/cobertura_bronze.json")
