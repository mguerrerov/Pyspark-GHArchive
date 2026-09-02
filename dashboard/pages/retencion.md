---
title: 3 · Proyectos que ganan o pierden contribuyentes
---

Un contribuyente pertenece a la cohorte del primer mes en que se le ve **en
ese repositorio**: la pregunta es qué proyectos ganan o pierden gente, así que
"nuevo" significa nuevo para el proyecto.

<Alert status=warning>

**"Nuevo" lo es solo respecto a la ventana observada.** Quien lleva años
contribuyendo a un repositorio aparece como nuevo si su primera actividad
dentro de la ventana cae en el primer mes. La cohorte inicial está inflada por
ese motivo y no debe compararse con las siguientes.

</Alert>

Las cuentas automáticas quedan excluidas de esta página: un bot no es un
contribuyente que se retenga o se pierda.

## Retención por cohorte

```sql retencion
-- Porcentaje de la cohorte que sigue activa en el repo, no actores en
-- absoluto: en absoluto las curvas caen de 5 millones a cientos de miles y
-- se aplastan contra el eje. El mes 0 es el 100 % por definicion y se omite.
-- La cohorte va como texto: con un DATE en `series` el LineChart salia
-- vacio en produccion, con los ejes dibujados y ninguna linea.
select
    strftime(cohorte_mes, '%Y-%m') as cohorte,
    mes_de_vida,
    actores,
    round(100.0 * actores
          / first_value(actores) over (partition by cohorte_mes order by mes_de_vida), 1)
        as pct_activos
from gharchive.p3_retencion_cohortes
qualify mes_de_vida > 0
order by cohorte_mes, mes_de_vida
```

<LineChart
    data={retencion}
    x=mes_de_vida
    y=pct_activos
    series=cohorte
    xAxisTitle="meses desde la primera contribución al repo"
    yAxisTitle="% de la cohorte que sigue activa"
    yFmt="0.0"
/>

La cohorte de agosto de 2025 retiene casi el doble que las demás por el efecto
de ventana descrito arriba: no es comparable. Sobre las cohortes limpias, entre
el 15 % y el 19 % vuelven al mes siguiente y entre el 5 % y el 7,5 % siguen a
los tres meses.

## Proyectos con más contribuyentes activos

```sql top_repos
select repo, sum(activos) as activos_acumulados, sum(nuevos) as nuevos_acumulados
from gharchive.p3_repos_saldo
group by 1
order by 2 desc
limit 20
```

<DataTable data={top_repos} rows=20>
    <Column id=repo title="Repositorio"/>
    <Column id=activos_acumulados title="Contribuyentes activos" fmt=num0 contentType=bar/>
    <Column id=nuevos_acumulados title="De ellos, nuevos" fmt=num0/>
</DataTable>
