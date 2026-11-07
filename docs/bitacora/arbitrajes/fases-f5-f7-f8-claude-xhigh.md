# Fases F5, F7 y F8 · Árbitro único de Claude, esfuerzo xhigh (2026-11-07): DEVUELTO

> Rama `feature/integracion-fases`, HEAD `c515ab1a`, rango `fe721e98..c515ab1a`. Árbitro único por decisión de Eugenio
> (sin árbitros por fase). Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO.** 4 MAYOR (2 de F5 vial y 2 de F5 ventana); F7 y F8 solo MENOR. Verde: pytest puntual de 23
archivos, vitest 340/340 en 13 archivos, `meta_datos` 4/4, ruff limpio, `core/` y los archivos congelados sin cambios.

## F5 vial
- **MAYOR P1.** `adapters/hoja_empresa/lector_apu_por_hoja.py:91-105` materializa todas las filas de todas las hojas hasta
  la `<dimension>` declarada, sin `reset_dimensions()` (que sí usa `lector.py:207-215`). Sonda: 8 hojas con A1 y CV20000,
  8.181 bytes, la guardia lo deja pasar, 16.000.000 de celdas y 132,1 MiB (con `reset_dimensions()`: 808 celdas, 10 MiB);
  con mil hojas, ~1 MB pide ~16 GiB. Pasa por `POST /v1/libros/apu-por-hoja` y el libro de presupuesto. Corrección:
  `reset_dimensions()`, leer solo las hojas con el prefijo y la del presupuesto, prueba roja que acote las celdas.
- **MAYOR P2.** `SILICE_PERFILES_LIBROS` no la fija nadie (`perfil_apu_por_hoja.py:47-48` dice que la fija el arranque;
  `operacion/lanzador.py:98-110` no) y el front no manda `perfil`: los perfiles locales (decisión provisional 5) no se
  alcanzan en el producto. Corrección: carpeta por omisión dentro de la carpeta de datos, prueba y manual técnico.
- MENOR P3 (coeficiente o precio inválido da 500), P4 (dos hojas con el mismo «Partida N°» se pisan sin aviso), P5 (`kgf →
  kg` en el perfil sin anotar como decisión provisional), P6 (README del CSV sin `transporte`; manual de usuario sin el
  desperdicio ni la auditoría por hoja; `manual_usuario.md:1140-1141`), P7 (la fase se cerró con `test_migraciones` en
  rojo; arreglado en `7aad2db3`), P8 (piso `pydantic>=2.0` con `exclude_if`), P9 (patrón de banda con punto de miles da 500).
- Sin defecto: desperdicio exacto, AH1 y su tolerancia, oráculos 2,0777625 y 0,81213 a mano, VR4 por banda, nombre de
  perfil validado, ruta con acceso, pantalla sin cálculo, migraciones aditivas, N4.

## F5 ventana
- **MAYOR V1.** `operacion/ventana.py:199` `private_mode=True` borra `localStorage` en cada arranque: el tamaño de letra
  (`comun/preferenciaDeLetra.ts`) y el zoom de la Hoja (`visor/zoomHoja.ts`) vuelven a «Normal». Corrección (decisión de
  Eugenio): `private_mode=False` con `storage_path` en la carpeta de datos, o sacar las preferencias de `localStorage`.
- **MAYOR V2.** V3 se dio por hecha sin los manuales: `docs/manual_instalacion.md:52-61` sigue diciendo que abre el
  navegador; el AVISO de `operacion/ventana.py:92-95` cita un manual que no explica WebView2; faltan `[interfaz] abrir_en`,
  `--sin-ventana`, el cierre y la segunda ejecución.
- MENOR: RF-184 promete de más (`window.pywebview` atiende mensajes internos; riesgo bajo con la CSP); licencia del SDK de
  WebView2 (resuelta después en `feature/pendientes-ventana`).
- Sin defecto: ajustes de pywebview, entorno de los hijos, respaldo, segunda ejecución, instalador, favicon.

## F7 Ayuda
- MENOR A1: «Quien administra no arma presupuestos» (`empiezaAqui.ts:25`) contradice la casilla para armar; con una sola
  persona el bloque del administrador no desaparece. A2: el oráculo de `catalogo.test.ts:140` acepta comentarios.
- Sin defecto: `/v1/cuentas` solo con su permiso, foco con `?tema=`, enlaces que preguntan antes de salir, nombres.

## F8 Cierre
- MENOR C1: quedan sin tilde «Esta version esta en solo lectura…» (`aplicacion/hoja_guardado.py:77`, no congelado) y no se
  anotó. C2: restos de la ruta vieja de Pendientes; «en este caso» en `precios_empresa/logica.ts:14`.
- Sin defecto: rutas retiradas sin referencias, poda del silabeo con fallo en voz alta, N1, guardia de «esta carpeta».

## Integración
- MENOR I1: `docs/ESTADO.md` dice que quedan 14 «en este caso» y omite lo que dejó F8. I2: nadie pasó la rama integrada
  por el navegador. I3: `2467b162` aflojó el oráculo de `test_humo_piezas` (mira el id, no la ruta canónica).
- Sin defecto: cadena de migraciones única, `docs/api.json`, ERS sin ID repetidos, DESIGN.md, choque F7/F8 resuelto.

## TDD
Todos los rojos tocan solo pruebas y van antes de su verde; muestreados uno o más por fase. Casi todos fallan porque falta
el módulo: valen, pero son débiles. F7 usó un solo rojo para A1–A4. Sin negativos que acepten un defecto.
