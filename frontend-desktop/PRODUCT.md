# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Ingeniero de costos de la empresa (constructora de obra civil en Venezuela) que **audita** libros de presupuesto
en Excel, propios o de terceros: abre el libro, ve dónde está cada hallazgo sobre la hoja original y decide qué
corregir. Confirmado por Eugenio el 2026-10-18. Quien arma el presupuesto y la gerencia son usuarios secundarios
de esta interfaz (roles `arma` y `revisa` de la instalación; el administrador no audita).

## Product Purpose

Sílice audita el libro de presupuesto de la empresa (`POST /v1/libros/auditoria`, reglas L1-L11) y la interfaz
nueva lo muestra **tal como se ve en Excel**, con cada hallazgo marcado sobre su celda. Éxito: el auditor llega de
un hallazgo a su celda y de una celda a su hallazgo sin buscar, y ve la cifra exacta (lo que dice el libro frente a
lo que calcula Sílice) sin abrir otra pantalla. La franja de indicadores presenta en centésimas (RS2-12) y el valor
exacto está siempre a un toque, en el tooltip de cada indicador.

## Positioning

El libro original es la evidencia y no se toca: la interfaz es una lente de solo lectura sobre la hoja de la
empresa, no una hoja nueva ni un tablero de resúmenes. Las cifras las pone el sistema (Decimal, desde la API); la
interfaz no calcula montos.

## Operating Context

- Laptop de 13-15 pulgadas, a veces en obra con luz variable; también monitor de oficina. Resolución mínima de
  diseño 1366×768, sin desplazamiento horizontal de la página.
- Libros de la plantilla de la empresa: PORTADA, INSUMOS, `APU-nn`, PRESUPUESTO, RESUMEN, MEDICIONES, CRONOGRAMA…
  (`tests/fixtures/libros_empresa.py`). Los libros reales son confidenciales y nunca entran al repositorio.
- Navegador de la propia PC o de otra PC de la red local; el FastAPI de la instalación sirve la interfaz en `/app`.
- La interfaz Streamlit de la 1.0.0 sigue siendo la principal mientras se migra (RT-4).

## Capabilities and Constraints

- Sin red externa (RNF-08): nada de CDN, fuentes alojadas en el propio servidor.
- Sin secretos en el navegador (RT-9): cookie de sesión `HttpOnly`, nunca claves en `localStorage` ni en el HTML.
- Severidades del núcleo: INFO, ADVERTENCIA, ERROR, CRITICO (`core.contracts.verificacion.Severidad`).
- Montos como texto decimal (`"1586.61"`), nunca `float`.
- Fuera de esta versión: corregir celdas (Capa Delta, sesión 3), arenera (sesión 4), escritorio Tauri (sesión 5).

## Brand Commitments

- Nombre: **Sílice**. Idioma: español de Venezuela, registro técnico y llano.
- Referencias obligatorias de Eugenio (RS-6): **IBM Carbon** (densidad de tablas, colores de severidad, morado
  para precios atípicos), **SAP Fiori** (cada indicador con valor, meta y desviación) e **IBCS** (la variación se
  colorea favorable/desfavorable, no positiva/negativa).
- Lo que lo haría sentirse mal (Eugenio, 2026-10-18): que parezca plantilla de IA, que esconda cifras, que cambie
  lo que ya funciona y las animaciones.

## Evidence on Hand

- Libro sintético con memoria de cálculo a mano: `tests/fixtures/libros_empresa.py` (`libro_limpio()`, siembras
  H1-H18). Todos los nombres son inventados.
- Dos libros reales de la empresa anonimizados con `scripts/anonimizar_libro.py` (B-3), **fuera del repositorio**:
  solo para verificación manual en el navegador; nunca se versionan. No se inventan clientes, obras ni montos reales.

## Product Principles

1. La evidencia primero: la hoja original ocupa la pantalla; los resúmenes la acompañan, no la tapan.
2. Ninguna cifra escondida: todo hallazgo muestra su celda, su valor y su impacto a la vista. La franja presenta en
   centésimas (RS2-12) y el valor exacto está siempre a un toque, en el tooltip.
3. El color significa algo: severidad en la hoja, favorable/desfavorable en las variaciones; nunca decoración.
4. Lo que funciona no se rompe: Streamlit convive hasta que la interfaz nueva cubra lo mismo.

## Accessibility & Inclusion

WCAG 2.1 AA: contraste de texto ≥ 4,5:1, de elementos gráficos ≥ 3:1; el color nunca va solo (ícono y texto en
cada estado); navegación completa con teclado; `prefers-reduced-motion` respetado.
