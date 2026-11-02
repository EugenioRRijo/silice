# Hoja 3b-3: contrato de las rutas R9 a R14 (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Fuente:** diseño §4.1, §4.3 y §6.1 (fila 3b-3).
Este documento se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-19-hoja-3b3-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## Reglas comunes (como R1 a R8)

- Prefijo `/v1/hoja`; todo `Cache-Control: no-store` (también en errores); el 422 es `{"detalle": "Los datos de la hoja no
  tienen la forma esperada: escriba cada celda como texto."}` sin repetir lo enviado; errores `{"detalle": str}`.
- **R9, R10 y R11** son vistas del borrador vivo: solo cuenta (con `X-Silice-Clave`, 403 «La hoja del proyecto se edita y se
  guarda con una cuenta; la clave de API no sirve.»), rol `arma` (`rita` 403 «Su cuenta no tiene permiso para esta
  acción.»), `id` de borrador de MI ficha (si no, 404 con el texto fijo de R3; 409 si el caso cambió).
- **R12, R13 y R14** leen una versión GUARDADA: clave de API **o** sesión con `EDITAR_HOJA`. No usan borrador; el front las
  pide con `proyecto` (código o nombre, como R1) y `version` (código, p. ej. `001`). Proyecto inexistente: 404 «El proyecto
  «Z» no existe en este caso.»; versión inexistente: 404 «El proyecto '…' no tiene una version '…': elija una de la lista.»
  (texto de la clásica, sin tildes). `proyecto` y `version` ≤ 500 caracteres; faltar cualquiera: 422.
- Montos: `Monto = {texto: str, exacto: str}` (`texto` a 2 decimales, `exacto` sin redondear ni notación científica). Ningún
  `float`. Los conteos son enteros. La interfaz no calcula: muestra `formatoEsVe(texto)` y deja `exacto` en el `title`.

## R9 `GET /v1/hoja/borradores/{id}/vistas/equilibrio` → `VistaEquilibrioRespuesta`

```
{ estado: "calculado" | "no_aplicable" | "no_existe" | "no_se_alcanza",
  moneda: str,
  venta: Monto, costo_variable: Monto, costo_fijo: Monto, utilidad: Monto,
  punto: Monto | null,            # null si el estado no lo permite
  porcentaje: Monto | null,       # punto / venta × 100 (texto «56.60»)
  periodo: str | null,            # etiqueta de la curva donde se alcanza («Dia 23 …»)
  fraccion_periodo: str | null,   # fracción 0 a 1 de ese período, exacta, como texto
  mensaje: str }                  # texto_equilibrio de la clásica: la frase del caso
```
Oráculo OF-001 (v001): costo variable 2137.44, punto 1530.49, porcentaje 56.60, periodo empieza por «Dia 23». OF-001 v002
(administración 0.20): total 2821.42, punto 1763.39, porcentaje 62.50. «No aplica» (sin ventas) no trae `punto` ni `porcentaje`.

## R10 `GET /v1/hoja/borradores/{id}/vistas/parametros` → `VistaParametrosRespuesta`

```
{ campos: [ {clave: "fcas"|"bono_alimentacion"|"administracion"|"utilidad", rotulo: str, valor: str} ],  # 4, en ese orden
  moneda_proyecto: str | null,    # null si el borrador no tiene versión abierta
  total: Monto,
  puede_convertir: bool }         # versión abierta y el rol tiene CONVERTIR_Y_REAJUSTAR
```
`valor` es el texto exacto del parámetro del borrador (`str(Decimal)`, p. ej. `0.15`). Son de lectura en 3b (se editan en 3c).

## R11 `GET /v1/hoja/borradores/{id}/vistas/auditoria` → `InformeAuditoriaRespuesta`

Es `api/esquemas_informe.InformeAuditoriaRespuesta` tal cual (`codigo_presupuesto, cumple, veredicto, total_hallazgos,
por_severidad, reglas_evaluadas, hallazgos[{numero, regla, severidad, partida, descripcion, impacto, observado, esperado,
origen[]}], sin_hallazgos`). Incluye **R17** (conexión de cada punto) ligada al espacio vigente del borrador. `origen` trae
las claves `esp_puntos:P2` etc. (el enlace «Ver en Auditoría» de 3b-F6b filtra por ese valor). Descripciones en texto plano.

## R12 `GET /v1/hoja/precios?proyecto=&version=` → `PreciosHojaRespuesta`

```
{ moneda: str,                     # moneda de la lista de precios de la versión
  fecha_evaluacion: "AAAA-MM-DD",  # hoy en el servidor
  columnas: [ {clave, rotulo, numerica: bool} ],   # 21, en el orden de la clásica
  filas: [ FilaPrecio ] }          # ordenadas por código de insumo
FilaPrecio = { insumo, codigo, tipo, precio: Monto, lista, moneda, fecha_precio: "AAAA-MM-DD",
               tasa: Monto|null, fecha_tasa: "AAAA-MM-DD"|null, referencia, cotizacion, moneda_original,
               precio_original: Monto|null, fuente_tasa, fuente, propio: "propio"|"heredado"|"",
               erosion_usd: Monto|null, erosion_bs: Monto|null,
               erosion_pct: Monto|null,      # ya multiplicado por 100 (texto «26.37»)
               erosion_indice: Monto|null,   # null siempre salvo que se le dé serie (hoy no): mostrar la columna solo si algún valor viene
               estado: str }       # «OK» o los avisos de origen, R11 y R12 separados por «; »
```
Columnas (clave → rótulo, `numerica`): `insumo` Insumo · `codigo` Código · `tipo` Tipo · `precio` Precio (n) · `lista` Lista ·
`moneda` Moneda · `fecha_precio` Fecha del precio · `tasa` Tasa (n) · `fecha_tasa` Fecha de la tasa · `referencia` Referencia ·
`cotizacion` Cotización · `moneda_original` Moneda original · `precio_original` Precio original (n) · `fuente_tasa` Fuente de la
tasa · `fuente` Fuente · `propio` Propio/heredado · `erosion_usd` Erosión USD (n) · `erosion_bs` Erosión Bs (n) · `erosion_pct`
Erosión % (n) · `erosion_indice` Erosión por índice (n) · `estado` Estado. La `tasa` puede tener más de dos decimales: mostrar
su `exacto`. Solo lee: no escribe nada.

## R13 `GET /v1/hoja/precios/atipicos?proyecto=&version=` → `AtipicosRespuesta`

Mismo esquema que `GET /v1/precios-empresa/listas/{id}/atipicos` (ahora definido en `api/esquemas_atipicos.py`, una sola copia):
`{disponible: bool, avisos: [{nivel: "info"|"success", texto}], variaciones: [{insumo, porcentaje, porcentaje_exacto, desde,
hasta, severidad, descripcion}]}`. Busca sobre los insumos de la versión. Sin el extra `ml`: `disponible=false` y el aviso
«La búsqueda de variaciones atípicas necesita el extra `ml` …». Solo lee. El rótulo del botón es «Buscar variaciones atípicas
de precio».

## R14 `GET /v1/hoja/trazabilidad?proyecto=&version=` → `TrazabilidadHojaRespuesta`

```
{ versiones: [ {codigo, fecha, motivo, origen, vigente, descartada, cambios} ],   # como R1; motivo "" = «elaborada»
  registros: [ {objeto, clave, campo, antes, despues, fuente, responsable, fecha_hora: "AAAA-MM-DDTHH:MM:SS"} ],
  vacio_mensaje: str | null }     # «Esta versión no nació de una edición: no tiene registros de cambio.» si no hay registros
```
`registros` son los de la versión pedida, en el orden en que se guardaron. Oráculo: la 002 de una edición de cantidad trae
`("cantidad", clave, "cantidad", "3", "5", fuente, responsable)`.

## Lo que NO cambia
Rutas R1 a R8, `api/rutas/precios_empresa.py` (solo importa ahora el esquema de atípicos), `ui/*`, `core/`, `asistente/`.
La Hoja no se activa en el menú.
