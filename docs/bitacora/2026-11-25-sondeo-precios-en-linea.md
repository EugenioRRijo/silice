# Sondeo: ¿hay precios de materiales publicados en línea para Venezuela? (2026-11-25)

**Pregunta de Eugenio.** ¿Se puede usar un servicio de lectura automática de páginas (Apify) para traer
precios del mercado y comparar presupuestos de la zona, con una capa en línea y otra sin conexión?

**Qué se hizo.** Se buscaron 10 materiales de la clase A del reporte local de insumos críticos (la lista
vive solo en el equipo, porque sale de libros reales; aquí no se nombra cuáles son). Hubo dos pasadas:
el buscador web de Claude Code con nombres genéricos de materiales y la lectura directa de los listados de
Mercado Libre Venezuela y de una tienda venezolana de materiales con el lector de páginas de Claude Code
(una petición HTTP simple, sin Apify). No se evaluó la API oficial de Mercado Libre: queda pendiente para
el trabajo futuro.

**Qué salió.**

- El buscador general devolvió tiendas de Colombia, Perú, Chile, Argentina y México, y una guía de
  precios de un vendedor de software de presupuestos. Esa guía da rangos estimados, no precios
  observados, y no hubo ningún precio venezolano con fecha y vendedor.
- Los 10 listados de Mercado Libre Venezuela y la tienda venezolana respondieron **HTTP 403**: bloquean
  la lectura automática. Saltarse ese bloqueo con servidores intermediarios iría contra sus condiciones
  de uso, y no se hizo.
- Los presupuestos de otras empresas no son públicos. Lo más cercano serían las contrataciones públicas;
  que publiquen solo el monto y no los APU es una observación no verificada en este sondeo.

**Conclusión.**

1. Un robot de lectura de páginas no es viable hoy como fuente del estudio de mercado. Mercado Libre
   Venezuela y la tienda consultada bloquean la lectura automática, y el buscador solo trajo tiendas de
   otros países y rangos estimados. Qué tipo de precio publican las tiendas venezolanas (al detal, al
   mayor) queda sin observar; se confirma a mano (punto 4).
2. El diseño de dos capas sí es coherente con Sílice. Un recolector aparte produce un archivo fechado
   con su fuente, compatible con la importación de listas (UC‑02 lleva moneda y fecha por lista; UC‑17
   admite fecha, fuente y referencia por fila) o con la futura entrada de cotizaciones al estudio de
   mercado, y Sílice lo importa sin conexión (RNF‑08). Queda como recomendación de la tesis
   ([plan de redacción](../tesis/plan_redaccion.md), conclusiones y recomendaciones).
3. No se construye nada antes de la defensa: el congelamiento ya lo decidió el consejo del 2026-11-24
   ([acta](2026-11-24-consejo-auditoria-alertas-mercado.md)); el sondeo solo confirma que el raspado web
   tampoco serviría hoy. La lista del proveedor, que el consejo dejó en la lista cerrada de después de la
   defensa, es su hipótesis de trabajo; este sondeo no la evaluó.
4. Si Eugenio quiere confirmarlo a mano, basta abrir en el navegador 10 listados de Mercado Libre
   Venezuela y anotar cuántos tienen precio, de qué tipo de vendedor y con qué fecha. Son unos 20
   minutos y no dejan datos de la empresa en ningún lado.
