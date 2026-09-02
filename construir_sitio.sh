#!/usr/bin/env bash
# Construye el sitio completo que sirve Netlify en dist/:
#
#   dist/                 <- site/ (overview y BI del pipeline, HTML + Tailwind)
#   dist/dashboard/       <- dashboard/build (Evidence, basePath /dashboard)
#
# Es el mismo script en local y en Netlify (ver netlify.toml). El runner NO
# tiene el lago ni Python: todo lo que necesita ya esta commiteado en el
# repo (los Parquet agregados y los JSON de site/data/).
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$raiz"

echo "== 1/3 Evidence (dashboard/) =="
( cd dashboard
  npm ci
  npm run sources
  npm run build )

echo "== 2/3 Tailwind (site/) =="
( cd site
  npm ci
  npm run build )

echo "== 3/3 Ensamblar dist/ =="
rm -rf dist
mkdir -p dist/dashboard
# Solo lo que se sirve: ni la entrada de Tailwind, ni node_modules, ni package*.
cp site/index.html site/metricas.html dist/
cp -r site/assets site/data dist/
cp -r dashboard/build/. dist/dashboard/

echo
echo "dist/ listo:"
du -sh dist dist/dashboard | sed 's/^/  /'
grep -o 'href="/dashboard/_app/[^"]*"' dist/dashboard/index.html | head -1 \
  | sed 's/^/  basePath OK: /' \
  || { echo "  ERROR: el HTML de Evidence no lleva el basePath /dashboard"; exit 1; }
