"""Comprueba que cada cifra de site/data/pipeline.json esta donde dice estar.

Cada entrada del JSON lleva un campo `fuente` con `docs/metrics.md:NNN`. Este
script abre esa linea (o rango) y busca el valor en ella, en formato espanol
(1.234,5) o ingles (1234.5). Si no lo encuentra, lo dice. Es la red que evita
que el sitio publique un numero que ya no esta en la medicion.

Uso:
    python comprobar_sitio.py
Sale con 1 si alguna cifra no cuadra.
"""

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
METRICS = (RAIZ / "docs" / "metrics.md").read_text(encoding="utf-8").splitlines()
JSON = json.loads((RAIZ / "site" / "data" / "pipeline.json").read_text(encoding="utf-8"))

# Campos que llevan el valor a comprobar, por orden de preferencia.
CAMPOS_VALOR = ("valor", "filas", "gib", "segundos", "merges", "errores", "eventos")
CAMPOS_NOMBRE = ("etiqueta", "titulo", "modelo", "capa", "paso", "clave", "mes", "momento", "lote", "variante")


def formatos(v) -> set[str]:
    """Todas las formas en que el valor puede estar escrito en metrics.md."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        return {str(v), f"{v:,}".replace(",", ".")}
    out = {str(v), str(v).replace(".", ",")}
    for d in (1, 2, 3):
        out.add(f"{v:.{d}f}".replace(".", ","))
        out.add(f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return out


def recoger(obj, salida):
    if isinstance(obj, dict):
        if isinstance(obj.get("fuente"), str):
            nombre = next((obj[c] for c in CAMPOS_NOMBRE if c in obj), "?")
            valor = next((obj[c] for c in CAMPOS_VALOR if c in obj), None)
            # Cuando el JSON guarda el valor en una forma distinta a la del
            # documento (segundos frente a "7 h 17 min", un 6 frente a
            # "seis"), la entrada dice que texto hay que buscar.
            texto = obj.get("comprobado") or (obj.get("etiqueta") if "segundos" in obj else None)
            salida.append((nombre, obj["fuente"], valor, texto))
        for v in obj.values():
            recoger(v, salida)
    elif isinstance(obj, list):
        for v in obj:
            recoger(v, salida)


def main() -> int:
    entradas = []
    recoger(JSON, entradas)
    fallos = 0
    comprobadas = 0
    for nombre, fuente, valor, texto in entradas:
        for m in re.finditer(r"docs/metrics\.md:(\d+)(?:-(\d+))?", fuente):
            a = int(m.group(1))
            b = int(m.group(2) or a)
            if b > len(METRICS):
                print(f"FUERA DE RANGO  {nombre!r}: {fuente}")
                fallos += 1
                continue
            bloque = " ".join(METRICS[a - 1:b])
            if texto:
                candidatos = {texto}
            elif isinstance(valor, (int, float)) and valor != 0:
                candidatos = formatos(valor)
            else:
                continue
            comprobadas += 1
            if not any(c in bloque for c in candidatos):
                print(f"NO CUADRA  {str(nombre)[:44]:44} {fuente:24} valor={valor}")
                print(f"           linea: {bloque[:100]}")
                fallos += 1
    print(f"\n{len(entradas)} entradas con fuente, {comprobadas} valores comprobados, {fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
