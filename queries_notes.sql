select * from precios_supermercado;

select * from precios_producto 
where marca is null
order by fecha_captura desc;

select * from precios_producto_hist;


update precios_producto set marca = '&JOY' where nombre like '% &AMP;JOY %'

select distinct marca from precios_producto order by 1

select count(*) from (select distinct marca from precios_producto) as marcas

select * from precios_producto where marca like '%&AMP%'