# Sondeo: ¿hay precios de materiales publicados en línea para Venezuela? (2026-11-25)

**Pregunta de Eugenio.** ¿Se puede usar un servicio de lectura automática de páginas (Apify) para traer
precios del mercado y comparar presupuestos de la zona, con una capa en línea y otra sin conexión?

**Qué se hizo.** Se buscaron 10 materiales de la clase A del reporte local de insumos críticos (la lista
vive solo en el equipo, porque sale de libros reales; aquí no se nombra cuáles son). Hubo dos pasadas:
el buscador general con nombres genéricos de materiales y la lectura directa de los listados de Mercado
Libre Venezuela y de una tienda venezolana de materiales.

**Qué salió.**

- El buscador general devolvió tiendas de Colombia, Perú, Chile, Argentina y México, y una guía de
  precios de un vendedor de software de presupuestos. Esa guía da rangos estimados, no precios
  observados, y no hubo ningún precio venezolano con fecha y vendedor.
- Los 10 listados de Mercado Libre Venezuela y la tienda venezolana respondieron **HTTP 403**: bloquean
  la lectura automática. Saltarse ese bloqueo con servidores intermediarios iría contra sus condiciones
  de uso, y no se hizo.
- Los presupuestos de otras empresas no son públicos. Lo más cercano son las contrataciones públicas,
  que publican el monto total y no los APU.

**Conclusión.**

1. Un robot de lectura de páginas no es viable hoy como fuente del estudio de mercado. Las tiendas lo
   bloquean, y lo que sí se ve es precio al detal o estimado, no el precio que cotiza un proveedor.
2. El diseño de dos capas sí es coherente con Sílice. Un recolector aparte produce un archivo fechado
   con su fuente, y Sílice lo importa sin conexión como cualquier lista (UC‑02, RNF‑08). Queda como
   recomendación de la tesis ([plan de redacción](../tesis/plan_redaccion.md), conclusiones y
   recomendaciones).
3. No se construye nada antes de la defensa: el congelamiento sigue en pie, según el consejo del
   2026-11-24 ([acta](2026-11-24-consejo-auditoria-alertas-mercado.md)). La fuente más prometedora es
   la lista del proveedor, que ya está en la lista cerrada de después de la defensa.
4. Si Eugenio quiere confirmarlo a mano, basta abrir en el navegador 10 listados de Mercado Libre
   Venezuela y anotar cuántos tienen precio, de qué tipo de vendedor y con qué fecha. Son unos 20
   minutos y no dejan datos de la empresa en ningún lado.
