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

<Alert status=warning>

**Entre el 9 de octubre y el 1 de diciembre de 2025 la fuente no publica si un
PR se mergeó.** Hasta el 8 de octubre el merge llega como acción `closed` con el
campo `merged` del pull request; desde el 2 de diciembre llega como una acción
propia, `merged`. En medio no llega de ninguna de las dos formas: el pull
request del payload viene recortado y la acción todavía no existe. Comprobado
en el JSON original, no deducido: en todo noviembre hay **cero** merges
observados, frente a unos 2,2 millones al mes en los meses vecinos.

Las latencias **hasta el merge** excluyen los PRs abiertos en ese tramo. Sin
ese filtro, los únicos supervivientes son los que se mergearon tan tarde que el
evento cayó ya en diciembre, y su mediana sale en 34.475 minutos en vez de los
2 minutos de un mes sano. Las latencias **hasta el primer review** sí incluyen
el tramo: los eventos de review siguen llegando con normalidad.

Queda un sesgo que no se puede corregir con estos datos: un PR abierto antes
del 9 de octubre y mergeado dentro del tramo pierde su merge y cuenta aquí como
no mergeado. Eso hunde la cobertura de las cohortes de septiembre y octubre en
el último gráfico de la página.

</Alert>

```sql mediana_global
-- Mediana del periodo completo, calculada sobre las filas de PR. Antes esta
-- tabla hacia la media de las medianas mensuales, que con meses de volumen muy
-- desigual no es la mediana de nada.
select
    autor_clase,
    prs,
    con_merge_observable,
    mediana_min_review as min_review,
    mediana_min_merge  as min_merge
from gharchive.p2_latencias_globales
where cohorte_madura
order by prs desc
```

<DataTable data={mediana_global}>
    <Column id=autor_clase title="Clase"/>
    <Column id=prs title="PRs" fmt=num0/>
    <Column id=con_merge_observable title="Merge medible" fmt=num0/>
    <Column id=min_review title="1er review (min)" fmt=num1/>
    <Column id=min_merge title="Merge (min)" fmt=num1/>
</DataTable>

Son medianas del periodo entero, no medias de medianas mensuales. La columna de
merge se calcula solo sobre los PRs con merge medible, que es la que va al lado.

<Alert status=warning>

**"Los bots" no existen como grupo aquí.** Juntar todas las cuentas automáticas
en una sola línea invierte la conclusión de esta página. Un `bot_ci` mergea en
**0,1 min**, y un `bot_dependencias` tarda **184,4 min**: cien veces más que un
humano, porque su PR espera a que alguien lo apruebe. Agregados juntos, el peso
de CI arrastra la media y sale que "los bots mergean casi al instante", que es
falso para tres de las cuatro clases. Por eso ningún gráfico ni tabla de esta
página colapsa las clases automáticas.

</Alert>

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
