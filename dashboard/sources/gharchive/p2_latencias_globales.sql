-- Agregado exportado por exportar_gold.py desde gold. La ruta es relativa a
-- la raiz del proyecto de Evidence.
select * from read_parquet('sources/gharchive/p2_latencias_globales.parquet')
