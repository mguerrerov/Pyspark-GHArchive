/* Pinta KPIs, tablas y graficos a partir de data/negocio.json y
   data/pipeline.json. Sin framework: cada grafico es una funcion que recibe
   los datos y devuelve una opcion de ECharts. Las paginas declaran que
   graficos quieren con elementos <div data-grafico="nombre">. */

const CLASES = {
  humano:           { color: 'serie-1', etiqueta: 'humano' },
  bot_dependencias: { color: 'serie-2', etiqueta: 'bot de dependencias' },
  bot_ci:           { color: 'serie-3', etiqueta: 'bot de CI' },
  bot_otro:         { color: 'serie-4', etiqueta: 'otro bot' },
  agente_ia:        { color: 'serie-5', etiqueta: 'agente de IA' },
};
const ORDEN_CLASES = Object.keys(CLASES);

const css = (nombre) => getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
const colorClase = (clase) => css(`--color-${CLASES[clase].color}`);

const fmt = {
  entero: (n) => n == null ? '—' : new Intl.NumberFormat('es-ES').format(Math.round(n)),
  dec: (n, d = 1) => n == null ? '—' : new Intl.NumberFormat('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d }).format(n),
  pct: (n, d = 1) => n == null ? '—' : fmt.dec(n, d) + ' %',
  compacto: (n) => {
    if (n == null) return '—';
    if (Math.abs(n) >= 1e9) return fmt.dec(n / 1e9, 2) + ' mil M';
    if (Math.abs(n) >= 1e6) return fmt.dec(n / 1e6, 1) + ' M';
    if (Math.abs(n) >= 1e3) return fmt.dec(n / 1e3, 0) + ' k';
    return fmt.entero(n);
  },
  horas: (s) => {
    if (s == null) return '—';
    if (s < 120) return fmt.dec(s, 0) + ' s';
    if (s < 7200) return fmt.dec(s / 60, 0) + ' min';
    return fmt.dec(s / 3600, 1) + ' h';
  },
  mes: (iso) => {
    const [a, m] = iso.split('-');
    return ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'][+m - 1] + ' ' + a.slice(2);
  },
};

/* ------------------------------------------------------------ base ECharts */
function base(extra = {}) {
  const tinta2 = css('--tinta-2'), tinta3 = css('--tinta-3'), rejilla = css('--rejilla');
  return {
    animationDuration: 400,
    textStyle: { fontFamily: css('--font-sans') || 'system-ui' },
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: css('--panel'), borderColor: css('--borde'),
      textStyle: { color: css('--tinta'), fontSize: 12 },
      axisPointer: { type: 'line', lineStyle: { color: tinta3 } },
    },
    legend: { top: 0, left: 0, icon: 'circle', itemWidth: 9, itemHeight: 9, textStyle: { color: tinta2, fontSize: 12 } },
    xAxis: { axisLine: { lineStyle: { color: rejilla } }, axisTick: { show: false }, axisLabel: { color: tinta3, fontSize: 11 }, splitLine: { show: false } },
    yAxis: { axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: tinta3, fontSize: 11 }, splitLine: { lineStyle: { color: rejilla } } },
    ...extra,
  };
}
const linea = (nombre, datos, color, extra = {}) => ({
  name: nombre, type: 'line', data: datos, showSymbol: false, symbolSize: 8,
  lineStyle: { width: 2, color }, itemStyle: { color }, emphasis: { focus: 'series' }, ...extra,
});
const barra = (nombre, datos, color, extra = {}) => ({
  name: nombre, type: 'bar', data: datos, barMaxWidth: 28,
  itemStyle: { color, borderRadius: [4, 4, 0, 0] }, ...extra,
});
const barraH = (nombre, datos, color, extra = {}) => ({
  name: nombre, type: 'bar', data: datos, barMaxWidth: 22,
  itemStyle: { color, borderRadius: [0, 4, 4, 0] }, ...extra,
});
function ejeCategorias(cats, extra = {}) { return { type: 'category', data: cats, ...extra }; }
function fusion(a, b) { return Object.assign({}, a, b, { xAxis: Object.assign({}, a.xAxis, b.xAxis), yAxis: Object.assign({}, a.yAxis, b.yAxis) }); }

/* ------------------------------------------------------------ graficos */
const GRAFICOS = {
  // P1: cuota mensual de eventos de PR que no son de humanos, y la de agentes.
  p1_cuota(n) {
    const meses = n.p1.cuota_mensual.map(r => fmt.mes(r.mes));
    return fusion(base(), {
      tooltip: { valueFormatter: v => fmt.pct(v) },
      xAxis: ejeCategorias(meses, { boundaryGap: false }),
      yAxis: { type: 'value', min: 0, max: 50, axisLabel: { formatter: '{value} %' } },
      series: [
        linea('no humano (todas las clases)', n.p1.cuota_mensual.map(r => r.pct_no_humano), colorClase('bot_ci'), { areaStyle: { opacity: 0.08 } }),
        linea('agente de IA', n.p1.cuota_mensual.map(r => r.pct_agente_ia), colorClase('agente_ia')),
      ],
    });
  },
  // P1: reparto mensual por clase, apilado al 100 %.
  p1_clases(n) {
    const meses = [...new Set(n.p1.mensual_por_clase.map(r => r.mes))];
    const totales = Object.fromEntries(meses.map(m => [m, n.p1.mensual_por_clase.filter(r => r.mes === m).reduce((s, r) => s + r.eventos, 0)]));
    return fusion(base(), {
      tooltip: { valueFormatter: v => fmt.pct(v) },
      xAxis: ejeCategorias(meses.map(fmt.mes)),
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value} %' } },
      series: ORDEN_CLASES.map(c => barra(CLASES[c].etiqueta,
        meses.map(m => { const r = n.p1.mensual_por_clase.find(x => x.mes === m && x.actor_clase === c); return r ? +(100 * r.eventos / totales[m]).toFixed(2) : 0; }),
        colorClase(c), { stack: 'total', itemStyle: { color: colorClase(c), borderColor: css('--panel'), borderWidth: 1 } })),
    });
  },
  // P2: mediana de minutos hasta el merge, por clase, en escala log.
  p2_merge(n) {
    const filas = [...n.p2.por_clase].sort((a, b) => a.mediana_min_merge - b.mediana_min_merge);
    return fusion(base({ grid: { left: 8, right: 60, top: 8, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br>mediana: <b>${fmt.dec(p.value)} min</b>` },
      xAxis: { type: 'log', logBase: 10, min: 0.05, axisLabel: { formatter: v => v < 1 ? fmt.dec(v) : fmt.entero(v), color: css('--tinta-3') }, splitLine: { lineStyle: { color: css('--rejilla') } }, axisLine: { show: false } },
      yAxis: ejeCategorias(filas.map(r => CLASES[r.autor_clase].etiqueta), { axisLabel: { color: css('--tinta-2'), fontSize: 12 }, splitLine: { show: false } }),
      series: [barraH('mediana min', filas.map(r => ({ value: r.mediana_min_merge, itemStyle: { color: colorClase(r.autor_clase), borderRadius: [0, 4, 4, 0] } })), null,
        { label: { show: true, position: 'right', color: css('--tinta'), formatter: p => fmt.dec(p.value) + ' min' } })],
    });
  },
  // P2: evolucion mensual de la mediana hasta el primer review por clase.
  p2_review_mensual(n) {
    const meses = [...new Set(n.p2.mensual.map(r => r.mes_apertura))];
    return fusion(base(), {
      tooltip: { valueFormatter: v => v == null ? '—' : fmt.dec(v) + ' min' },
      xAxis: ejeCategorias(meses.map(fmt.mes), { boundaryGap: false }),
      yAxis: { type: 'value', axisLabel: { formatter: '{value} min' } },
      series: ORDEN_CLASES.map(c => linea(CLASES[c].etiqueta, meses.map(m => (n.p2.mensual.find(x => x.mes_apertura === m && x.autor_clase === c) || {}).mediana_min_review ?? null), colorClase(c))),
    });
  },
  // P3: curva de retencion por cohorte. Las cohortes son una secuencia, asi
  // que van en un solo tono de azul, de claro a oscuro.
  p3_cohortes(n) {
    const cohortes = [...new Set(n.p3.cohortes.map(r => r.cohorte))];
    // El mes 0 es el 100 % por definicion y aplastaria la escala: se empieza en 1.
    const meses = [...new Set(n.p3.cohortes.map(r => r.mes_de_vida))].filter(m => m > 0).sort((a, b) => a - b);
    const azul = colorClase('humano');
    return fusion(base({ grid: { left: 8, right: 16, top: 56, bottom: 8, containLabel: true } }), {
      tooltip: { valueFormatter: v => v == null ? '—' : fmt.pct(v) },
      xAxis: ejeCategorias(meses, { name: 'meses desde la primera contribución al repo', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: css('--tinta-3'), fontSize: 11 } }),
      yAxis: { type: 'value', max: 30, axisLabel: { formatter: '{value} %' } },
      series: cohortes.map((c, i) => {
        const base0 = n.p3.cohortes.find(r => r.cohorte === c && r.mes_de_vida === 0).actores;
        const op = 0.35 + 0.65 * (i / Math.max(1, cohortes.length - 1));
        return linea(fmt.mes(c) + (i === 0 ? ' (inflada)' : ''),
          meses.map(m => { const r = n.p3.cohortes.find(x => x.cohorte === c && x.mes_de_vida === m); return r ? +(100 * r.actores / base0).toFixed(1) : null; }),
          azul, { lineStyle: { width: i === 0 ? 1.5 : 2, color: azul, opacity: op, type: i === 0 ? 'dashed' : 'solid' }, itemStyle: { color: azul, opacity: op } });
      }),
    });
  },
  p3_repos(n) {
    const filas = [...n.p3.top_repos].reverse();
    return fusion(base({ grid: { left: 8, right: 70, top: 8, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br>${fmt.entero(p.value)} contribuyentes activos acumulados` },
      xAxis: { type: 'value', axisLabel: { formatter: fmt.compacto }, splitLine: { lineStyle: { color: css('--rejilla') } }, axisLine: { show: false } },
      yAxis: ejeCategorias(filas.map(r => r.repo), { axisLabel: { color: css('--tinta-2'), fontSize: 11 }, splitLine: { show: false } }),
      series: [barraH('activos', filas.map(r => r.activos_acumulados), colorClase('humano'), { label: { show: true, position: 'right', color: css('--tinta-2'), fontSize: 11, formatter: p => fmt.compacto(p.value) } })],
    });
  },

  /* --------------------------------------------- BI del pipeline */
  embudo(p) {
    const filas = [...p.volumen.embudo].reverse();
    return fusion(base({ grid: { left: 8, right: 90, top: 8, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${fmt.entero(q.value)}</b> filas` },
      xAxis: { type: 'log', logBase: 10, axisLabel: { formatter: fmt.compacto }, splitLine: { lineStyle: { color: css('--rejilla') } }, axisLine: { show: false } },
      yAxis: ejeCategorias(filas.map(r => `${r.capa} · ${r.tabla}`), { axisLabel: { color: css('--tinta-2'), fontSize: 11 }, splitLine: { show: false } }),
      series: [barraH('filas', filas.map(r => ({ value: r.filas, itemStyle: { color: { bronze: colorClase('bot_dependencias'), silver: colorClase('bot_otro'), gold: colorClase('humano') }[r.capa], borderRadius: [0, 4, 4, 0] } })), null,
        { label: { show: true, position: 'right', color: css('--tinta-2'), fontSize: 11, formatter: q => fmt.compacto(q.value) } })],
    });
  },
  disco(p) {
    const filas = [
      { n: 'fuente .gz (año, proyección medida)', v: p.disco.capas[0].gib },
      { n: 'bronze', v: p.disco.capas[1].gib },
      { n: 'silver/eventos', v: p.disco.capas[2].gib },
      { n: 'silver/pr_eventos', v: p.disco.capas[3].gib },
      { n: 'agregados publicados', v: p.disco.kpis.find(k => k.id === 'export_mb').valor / 1024 },
    ].reverse();
    return fusion(base({ grid: { left: 8, right: 80, top: 8, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${q.value < 0.01 ? fmt.dec(q.value * 1024, 2) + ' MB' : fmt.dec(q.value, 1) + ' GiB'}</b>` },
      xAxis: { type: 'log', logBase: 10, min: 0.00005, axisLabel: { formatter: v => v >= 1 ? fmt.entero(v) + ' GiB' : fmt.dec(v * 1024, 0) + ' MB' }, splitLine: { lineStyle: { color: css('--rejilla') } }, axisLine: { show: false } },
      yAxis: ejeCategorias(filas.map(r => r.n), { axisLabel: { color: css('--tinta-2'), fontSize: 11 }, splitLine: { show: false } }),
      series: [barraH('GiB', filas.map(r => r.v), colorClase('humano'), { label: { show: true, position: 'right', color: css('--tinta-2'), fontSize: 11, formatter: q => q.value < 0.01 ? fmt.dec(q.value * 1024, 2) + ' MB' : fmt.dec(q.value, 1) + ' GiB' } })],
    });
  },
  compresion(p) {
    const v = p.disco.compresion_bronze_un_dia;
    return fusion(base({ grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${fmt.dec(q.value, 3)} GiB</b> · ratio ${fmt.dec(v[q.dataIndex].ratio_vs_gz, 3)}× · ${fmt.dec(v[q.dataIndex].segundos, 1)} s` },
      xAxis: ejeCategorias(v.map(r => r.variante), { axisLabel: { interval: 0, fontSize: 11 } }),
      yAxis: { type: 'value', axisLabel: { formatter: '{value} GiB' } },
      series: [barra('GiB de un día', v.map(r => r.gib), colorClase('humano'), { label: { show: true, position: 'top', color: css('--tinta-2'), fontSize: 11, formatter: q => fmt.dec(v[q.dataIndex].ratio_vs_gz, 2) + '× el .gz' } })],
    });
  },
  dbt_modelos(p) {
    const filas = [...p.tiempos.dbt_por_modelo].reverse();
    return fusion(base({ grid: { left: 8, right: 80, top: 8, bottom: 8, containLabel: true } }), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${filas[q.dataIndex].etiqueta}</b>${filas[q.dataIndex].pico_temporal_gib != null ? '<br>pico de temporal: ' + fmt.dec(filas[q.dataIndex].pico_temporal_gib, 1) + ' GiB' : ''}` },
      xAxis: { type: 'value', axisLabel: { formatter: v => fmt.dec(v / 3600, 0) + ' h' }, splitLine: { lineStyle: { color: css('--rejilla') } }, axisLine: { show: false } },
      yAxis: ejeCategorias(filas.map(r => r.modelo), { axisLabel: { color: css('--tinta-2'), fontSize: 11, fontFamily: css('--font-mono') }, splitLine: { show: false } }),
      series: [barraH('duración', filas.map(r => r.segundos), colorClase('humano'), { label: { show: true, position: 'right', color: css('--tinta-2'), fontSize: 11, formatter: q => filas[q.dataIndex].etiqueta } })],
    });
  },
  lotes_silver(p) {
    const v = p.volumen.lotes_silver;
    return fusion(base(), {
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${fmt.horas(q.value)}</b> · ${fmt.entero(v[q.dataIndex].filas)} filas leídas` },
      legend: { show: false },
      xAxis: ejeCategorias(v.map(r => r.lote.replace(' a ', ' → ')), { axisLabel: { interval: 0, fontSize: 10 } }),
      yAxis: { type: 'value', axisLabel: { formatter: v => fmt.dec(v / 60, 0) + ' min' } },
      series: [barra('segundos', v.map(r => r.segundos), colorClase('bot_otro'), { label: { show: true, position: 'top', color: css('--tinta-2'), fontSize: 11, formatter: q => fmt.horas(q.value) } })],
    });
  },
  degradacion(n) {
    const d = n.degradacion.diaria;
    const corte = n.degradacion.corte_pr;
    return fusion(base({ grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true } }), {
      tooltip: { valueFormatter: v => fmt.pct(v, 2) },
      xAxis: ejeCategorias(d.map(r => r.fecha), { boundaryGap: false, axisLabel: { formatter: v => fmt.mes(v.slice(0, 7)), interval: 29 } }),
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value} %' } },
      series: [
        linea('PullRequestEvent', d.map(r => r.pct_pr), colorClase('humano'), { areaStyle: { opacity: 0.1 } }),
        linea('PushEvent', d.map(r => r.pct_push), colorClase('bot_otro'), {
          markLine: { symbol: 'none', lineStyle: { color: css('--color-aviso'), type: 'dashed', width: 1.5 },
            label: { formatter: 'corte ' + corte, color: css('--color-aviso'), fontSize: 11, position: 'insideEndTop' },
            data: [{ xAxis: corte }] },
        }),
      ],
    });
  },
  merges(p) {
    const v = p.fuente.merges_por_mes;
    return fusion(base(), {
      legend: { show: false },
      tooltip: { trigger: 'item', formatter: q => `${q.name}<br><b>${fmt.entero(q.value)}</b> merges observados` },
      xAxis: ejeCategorias(v.map(r => fmt.mes(r.mes))),
      yAxis: { type: 'value', axisLabel: { formatter: fmt.compacto } },
      series: [barra('merges', v.map(r => ({ value: r.merges, itemStyle: { color: r.merges === 0 ? css('--color-aviso') : colorClase('humano'), borderRadius: [4, 4, 0, 0] } })), null,
        { label: { show: true, position: 'top', color: css('--tinta-2'), fontSize: 11, formatter: q => q.value === 0 ? 'cero' : fmt.compacto(q.value) } })],
    });
  },
  historico_bots(p) {
    const v = p.fuente.historico_bots_pct;
    return fusion(base(), {
      legend: { show: false },
      tooltip: { valueFormatter: x => fmt.pct(x, 2) },
      xAxis: ejeCategorias(v.map(r => String(r.anio)), { boundaryGap: false }),
      yAxis: { type: 'value', axisLabel: { formatter: '{value} %' } },
      series: [linea('% eventos de cuentas [bot]', v.map(r => r.pct), colorClase('bot_ci'), { showSymbol: true, areaStyle: { opacity: 0.08 }, label: { show: true, position: 'top', color: css('--tinta-2'), fontSize: 11, formatter: q => fmt.dec(q.value, 1) } })],
    });
  },
};

/* ------------------------------------------------------------ KPIs y tablas */
function pintarKpi(el, k) {
  const valor = typeof k.valor === 'number'
    ? (k.unidad === '%' ? fmt.dec(k.valor, 1) : Number.isInteger(k.valor) ? (k.valor >= 1e6 ? fmt.compacto(k.valor) : fmt.entero(k.valor)) : fmt.dec(k.valor, k.valor < 10 ? 2 : 1))
    : k.valor;
  const unidad = k.de != null ? `/ ${k.de}` : (k.unidad && k.unidad !== '%' ? k.unidad : (k.unidad === '%' ? '%' : ''));
  el.innerHTML = `<div class="valor">${valor}<span class="unidad">${unidad}</span></div>
    <div class="etiqueta">${k.etiqueta}</div>${k.detalle ? `<div class="detalle">${k.detalle}</div>` : ''}`;
  el.title = 'Fuente: ' + k.fuente;
}
function pintarKpis(contenedor, lista) {
  contenedor.innerHTML = '';
  for (const k of lista) { const d = document.createElement('div'); d.className = 'kpi'; pintarKpi(d, k); contenedor.appendChild(d); }
}
function tabla(contenedor, columnas, filas) {
  const th = columnas.map(c => `<th class="${c.num ? 'num' : ''}">${c.titulo}</th>`).join('');
  const tr = filas.map(f => '<tr>' + columnas.map(c => `<td class="${c.num ? 'num' : ''}" ${c.titleDe ? `title="${f[c.titleDe] || ''}"` : ''}>${c.render ? c.render(f) : f[c.campo]}</td>`).join('') + '</tr>').join('');
  contenedor.innerHTML = `<table class="tabla"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
}

/* ------------------------------------------------------------ arranque */
async function cargar(ruta) {
  const r = await fetch(ruta);
  if (!r.ok) throw new Error(`No se pudo leer ${ruta}: ${r.status}`);
  return r.json();
}

const instancias = [];
function pintarGraficos(n, p) {
  for (const el of document.querySelectorAll('[data-grafico]')) {
    const nombre = el.dataset.grafico;
    const fn = GRAFICOS[nombre];
    if (!fn) { console.warn('Grafico desconocido', nombre); continue; }
    // Los graficos de negocio y la degradacion leen negocio.json; el resto,
    // pipeline.json.
    const datos = (nombre.startsWith('p') || nombre === 'degradacion') ? n : p;
    const chart = echarts.init(el, null, { renderer: 'svg' });
    chart.setOption(fn(datos));
    instancias.push({ chart, fn, datos });
  }
}

window.addEventListener('DOMContentLoaded', async () => {
  try {
    const [n, p] = await Promise.all([cargar('data/negocio.json'), cargar('data/pipeline.json')]);
    window.DATOS = { n, p };
    if (typeof window.pintarPagina === 'function') window.pintarPagina(n, p, { pintarKpis, tabla, fmt, CLASES, ORDEN_CLASES, colorClase });
    pintarGraficos(n, p);
    const redibujar = () => instancias.forEach(i => i.chart.resize());
    window.addEventListener('resize', redibujar);
    // Al cambiar el tema del sistema los colores salen de las variables CSS,
    // asi que basta con volver a construir la opcion.
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      instancias.forEach(i => i.chart.setOption(i.fn(i.datos), true));
    });
  } catch (e) {
    console.error(e);
    document.querySelectorAll('[data-grafico]').forEach(el => el.innerHTML = `<p class="fuente">No se pudieron cargar los datos: ${e.message}</p>`);
  }
});
