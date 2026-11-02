# 2026-10-21 · Lector del BCV: solo las hojas necesarias

Decision de Eugenio: no subir el tope de 50 hojas; leer solo lo necesario sin sobrecargar el sistema.

## Que se leia y que hace falta
- Tasa (`2_1_2c26_smc.xls`, 64 hojas): una hoja por dia, nombre `DDMMAAAA`. Cada una aporta un valor de la
  serie, asi que las 64 SON necesarias (el tope de 50 las rechazaba todas, no una parte).
- INPC (`4_5_7.xls`): una sola hoja, `Base Diciembre 2007` (de `formatos.json`).

## Cambio (`adapters/bcv/libro.py`)
- Se deciden las hojas por nombre con `sheet_names()` (xlrd `on_demand=True`; openpyxl `sheetnames` en
  modo lectura) ANTES de abrir ninguna; las ajenas no se piden, no se materializan y se cuentan en
  `Libro.avisos` («hojas ajenas no leidas: N»).
- Necesaria = nombre de 8 digitos o la hoja del INPC. Sin ninguna: `FormatoNoReconocido` claro.
- Topes: `MAX_HOJAS_DECLARADAS = 256` (total del libro, se comprueba primero: un libro hostil con miles
  de hojas se rechaza sin pedir ninguna) y `MAX_HOJAS_LEIDAS = 100` (sobre las necesarias; un trimestre
  trae como mucho 92 dias). Se conservan el tope de 20 MB, 2 000 000 celdas por hoja, la verificacion
  del ZIP/macros y la firma OLE2/ZIP.

## Punto para el arbitro / Eugenio
El tope de LEIDAS no puede ser 50: la tasa de un trimestre legitimo necesita 64 (hasta 92). Se fijo en
100 sobre las leidas, y el total declarado en 256. Una hoja de tasa renombrada a algo que no sea fecha
ya no entra al informe (antes se rechazaba con motivo en el informe; ahora se ignora con aviso).
