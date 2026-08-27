---
title: 2 · Cuánto tarda un PR en revisarse y mergearse
---

Las latencias se calculan restando los instantes de los propios eventos, no
leyendo campos del pull request: es la única vía que funciona en los dos
formatos de la fuente, y mide cuándo GitHub emitió el hecho.

<Alert status=warning>

**Censura por los bordes de la ventana.** Un PR abierto antes del inicio no
tiene evento de apertura observable, y uno abierto al final puede no haberse
mergeado todavía. Los gráficos de esta página usan **solo cohortes maduras**:
PRs abiertos con al menos 30 días de margen dentro de la ventana. Sin ese
filtro, la media sale sesgada a la baja.

</Alert>

```sql mediana_global
select
    autor_clase,
    sum(prs)                    as prs,
    round(avg(mediana_min_review), 1) as min_review,
    round(avg(mediana_min_merge), 1)  as min_merge
from gharchive.p2_latencias_mensuales
where cohorte_madura
group by 1 order by 2 desc
```

<DataTable data={mediana_global}>
    <Column id=autor_clase title="Clase de autor"/>
    <Column id=prs title="PRs" fmt=num0/>
    <Column id=min_review title="Mediana min. hasta 1er review" fmt=num1/>
    <Column id=min_merge title="Mediana min. hasta merge" fmt=num1/>
</DataTable>

## Evolución de la latencia hasta el primer review

```sql evolucion
select mes_apertura, autor_clase, mediana_min_review, mediana_min_merge
from gharchive.p2_latencias_mensuales
where cohorte_madura
order by mes_apertura
```

<LineChart
    data={evolucion}
    x=mes_apertura
    y=mediana_min_review
    series=autor_clase
    yAxisTitle="minutos (mediana)"
/>

## Evolución de la latencia hasta el merge

<LineChart
    data={evolucion}
    x=mes_apertura
    y=mediana_min_merge
    series=autor_clase
    yAxisTitle="minutos (mediana)"
/>

## Cuántos PRs quedan fuera por cohorte inmadura

```sql madurez
select
    case when cohorte_madura then 'cohorte madura' else 'aún sin madurar' end as estado,
    sum(prs) as prs
from gharchive.p2_latencias_mensuales
group by 1
```

<DataTable data={madurez}>
    <Column id=estado title="Estado de la cohorte"/>
    <Column id=prs title="PRs" fmt=num0/>
</DataTable>

## Cuánta censura hay

Volumen de PRs que no pueden usarse para medir latencia, y por qué.

```sql censura
select
    mes,
    case
        when apertura_observada and merge_observado     then 'ciclo completo'
        when apertura_observada and not merge_observado then 'sin merge observado'
        when not apertura_observada and merge_observado then 'abierto antes de la ventana'
        else 'solo eventos intermedios'
    end as situacion,
    sum(prs) as prs
from gharchive.p2_censura
group by 1, 2
order by 1
```

<AreaChart
    data={censura}
    x=mes
    y=prs
    series=situacion
    type=stacked100
    title="Situación de los PRs observados"
/>
