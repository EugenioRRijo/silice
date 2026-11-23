---
name: constructor-gemini
description: >-
  Cómo construye Gemini (Neon, Hydrogen) un lote del front o del back de Sílice cuando Claude orquesta: sin
  ejecutar comandos, solo en los archivos del lote, con TDD (Claude separa rojo y verde), y siguiendo DESIGN.md,
  unslop, impeccable, las reglas de ECC (hookify) y la lectura «goldfish» de un recién llegado. Usar siempre que
  un encargo diga «construye» o «lote».
---

# Constructor Gemini de Sílice

Vigente desde el 2026-11-22 (pedido de Eugenio: «haz que tus trabajadores de gemini construyan según tus parámetros y md
actualizados ... siguiendo los hooks de ecc, golden fish, unslop e impeccable»). Claude orquesta y arbitra; Eugenio
decide. Lee antes [metodologia-silice](../metodologia-silice/SKILL.md) y, para el front,
[front-carbon-fiori-ibcs](../front-carbon-fiori-ibcs/SKILL.md) y `frontend-desktop/DESIGN.md`.

## Cómo se trabaja

- **No ejecutes ningún comando** (ni npm, ni git, ni pytest): solo lees y editas. Claude corre las pruebas, mide y hace
  los commits. Si no puedes comprobar algo leyendo, dilo en el informe.
- **Solo los archivos de tu lote** y sus pruebas al lado. Otros constructores editan otros archivos a la vez.
- **Verifica cada punto contra el código antes de cambiarlo.** Si el hallazgo es falso o la propuesta cambia el
  significado (lee qué hace el código), no lo cambies y explica por qué.
- **TDD:** por cada comportamiento o texto visible que cambies, primero la prueba (actualiza la que busca lo viejo o
  agrega una aserción nueva). Claude aparta tu código, ve la prueba en rojo, lo repone y ve el verde.
- **Informe final:** (1) archivos de prueba cambiados; (2) archivos de código cambiados; (3) por punto: hecho / no hecho y
  por qué / necesita back / fuera de lote.

## Reglas de ECC (hookify): lo que bloquea el repositorio

- `core/` no cambia sin expediente y aval del tutor. Tampoco `aplicacion/hoja.py`.
- Nada de Streamlit (se retiró el 2026-10-21).
- Ningún libro real, nombre de empresa ni dato derivado de ellos entra al repositorio: las pruebas usan casos ficticios.
- Los planes `PLAN_*.md` de la raíz son historia: no se editan.
- Un código de salida tras una tubería no prueba nada (eso lo vigila Claude).

## Unslop (adaptado a Sílice): que no parezca hecho por IA

- Español llano, en usted, sin exclamaciones ni saludos, sin palabras infladas (potente, inteligente, sin esfuerzo,
  impulsado por IA). Títulos y botones con mayúscula inicial y sin punto final.
- Sin numeración decorativa («01 ·»), sin rótulos en MAYÚSCULAS con tracking, sin emojis ni íconos de adorno, sin
  brillos, sombras de color ni degradados entre tonos. Un solo botón principal por zona.
- Cifras con coma decimal y punto de miles (`formatoEsVe`), `tabular-nums` en columnas; plurales reales (nunca «(s)»).
- Una comparación dice contra qué. Nada de jerga interna visible (ids, nombres de campo, «caso», inglés).
- Pesos de 600 como máximo; letra mínima de 0,75 rem; espaciados y radios en la rejilla de 4 px.
- **No es hallazgo** (decisiones de Eugenio): las animaciones, la paleta carbón y dorado, la familia tipográfica, los
  colores IBCS y los cuatro niveles de severidad, el tamaño de letra solo en Cuenta › Configuración.

## Impeccable: lo que el detector marca (Claude lo corre después de tu lote)

- Interlineado menor de 1,3 en texto de varias líneas; franjas gruesas a un lado de una tarjeta como adorno (la del
  indicador de selección de Carbon sí vale); imágenes rotas; contraste bajo; texto diminuto.
- Responsive con letra grande: nada de anchos fijos; una rejilla lleva `grid-template-columns: minmax(0, 1fr)` (con la
  implícita `auto` un hijo ancho estira la página); los hijos de flex llevan `min-inline-size: 0`; los ajustes que solo
  hacen falta con letra Grande o Muy grande van dentro de `con-letra-grande` o `por-debajo-del-umbral` de
  `frontend-desktop/src/marco/_umbrales.scss`. Claude lo mide con `scripts/recorrido_ux_playwright.py` a 768, 1024, 1366 y
  1920 px con las tres letras.

## Goldfish: que lo entienda alguien que llega sin contexto

La persona usuaria sabe de obras, partidas, APU y precios; no de software ni de gerencia de proyectos.

- Cada pantalla con cifras dice bajo su `h1`, en una línea, **para qué sirve** y, si hace falta, cómo leer la cifra
  principal (qué es bueno, qué es malo).
- Una sigla técnica correcta (EAC, SPI, CPI, P50, P80, FCAS, BCV, INPC, SHA-256) se queda, pero la primera vez lleva su
  explicación a la vista; el término va también al glosario (`frontend-desktop/src/comun/ayuda/textos.ts`).
- Un botón dice qué pasa al pulsarlo. Una leyenda no obliga a ir y venir: el nombre va junto al color o al código.
- Mismo nombre para la misma idea en todas las pantallas («Usar como precio real en Control de obra», «Código de
  verificación (SHA-256)», «carpeta» y no «caso»).
- **Textos que manda el servidor:** no se reescriben en la pantalla; se corrigen en el back (`api/`, `aplicacion/`, sin
  tocar `core/`) en un lote de back, con su prueba de Python.
