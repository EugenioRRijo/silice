# Pasada goldfish (lotes N1 y N2): lo que un recién llegado aún no entiende

> **Estado (2026-11-23):** pendiente. Los créditos de Gemini se agotaron antes de construirla (error 429). Claude
> corrigió ya los dos errores de fondo del glosario (N1, puntos 1 y 2: el CPI y el P50/P80, commit `5383c750`); en
> pantalla falta aplicar a Riesgo el texto nuevo de P50/P80. Todo lo demás está por hacer. Para retomarlo, dárselo
> tal cual a Neon (N1) y Hydrogen (N2) con la skill `constructor-gemini`.


Activa `.agents/skills/constructor-gemini/SKILL.md` (sin comandos, solo tu lote, TDD, informe). Rama
`feature/ui-aistudio-correcciones`. Un revisor «goldfish» (lector sin contexto) leyó los textos nuevos y pidió otra
pasada corta. Claude ya decidió los nombres; aplícalos tal cual. **Busca cada texto por su contenido** (las líneas que
cita el revisor son de un extracto, no del archivo).

## Nombres únicos (valen para los dos lotes)

- Riesgo: solo **«simulación»** (nunca «trayectoria» ni «escenario» en Riesgo). «Escenario» queda para Escenarios de precios.
- **«Incidencia en el cambio (%)»** donde hoy dice «Incidencia (%)», «Aporte al cambio (%)» o «Peso en el cambio (%)».
- **«Prueba con meses pasados»** para la comprobación hacia atrás de Riesgo; en pantalla «Meses probados», «Meses
  cubiertos por el P80» y «Cobertura (% de meses cubiertos)».
- **«Código de verificación de la clave (SHA-256)»** para la huella de la clave de firma y **«Código de verificación del
  archivo (SHA-256)»** para el del archivo entregado.
- **«Fecha de la revisión»** (Visor): cualquier mensaje que diga «fecha de auditoría» pasa a «fecha de la revisión».
- Ejemplos siempre como «por ejemplo, 0,15 = 15 %» (no «ej.» ni «Ejemplo:»).

## Lote N1 (glosario, Riesgo, Control, Reajuste)

Archivos: `frontend-desktop/src/comun/ayuda/`, `paginas/riesgo/`, `paginas/control/`, `paginas/reajuste/`,
`comun/CurvaPlanAvance.tsx`, `comun/VisualMeters.tsx`; sus pruebas.

1. **Glosario, P50/P80** (error de fondo, la frase se lee al revés): «En Riesgo, P50 es el total que no se supera en la
   mitad de las simulaciones; P80, el que no se supera en 8 de cada 10. La reserva recomendada es la diferencia entre el
   total base y el P80.» En Riesgo: «Costo probable (P50: no se supera en la mitad de las simulaciones)» y «Costo
   conservador (P80: no se supera en 8 de cada 10 simulaciones)».
2. **Glosario, CPI** (error de fondo, hoy se confunde con el SPI): «por debajo de 1,00 indica que se está gastando más de
   lo que vale lo ejecutado (sobrecosto)». Revisa que SPI diga «atraso frente a lo planificado».
3. Glosario: título «Prueba con meses pasados» (antes «Comprobación hacia atrás»); «Incidencia en el cambio (%)»;
   unifica INPC como «Índice Nacional de Precios al Consumidor (INPC)» en todas partes; si FCAS no está, agrégalo:
   «Factor de costos asociados al salario (FCAS)». MaPreX: agrega una entrada corta (referencia pública de precios de
   construcción en bolívares) si no existe.
4. Riesgo: «Número de repetición (semilla)» → «Semilla (número para obtener siempre el mismo resultado)».
5. Control: «Límite de atraso (SPI) para error» → «SPI mínimo antes de marcar «Error»»; igual con el CPI. «Sin proyectar
   inflación futura.» → «Estas cifras no incluyen inflación futura.». «Costo final estimado por partida (EAC del
   sistema)» → «Costo final estimado sumando cada partida (EAC)».
6. Curva (`CurvaPlanAvance.tsx`): «Línea gruesa: ejecutado y gastado» — **lee primero cómo se dibujan** EV y AC. Si
   comparten estilo, dale a AC uno propio (por ejemplo, gruesa punteada) y escribe una leyenda por serie: «Línea gruesa:
   ejecutado (EV) · Línea gruesa punteada: gastado (AC)». Si ya tienen estilos distintos, solo corrige la leyenda.
7. Reajuste: la parte fija con un solo nombre, «Parte del contrato que no se reajusta (R)»; «Estado del estudio:
   ${estado}.» → «Estado: ${estado}»; «Estudio preliminar al que reemplaza este cálculo definitivo (opcional)» →
   «Estudio preliminar que este cálculo reemplaza (opcional)».

## Lote N2 (precios, presupuesto, producción, entrega y administración)

Archivos: `paginas/hoja/`, `paginas/componer/`, `paginas/actualizacion/`, `paginas/mercado/`, `paginas/precios_empresa/`,
`paginas/produccion/`, `paginas/entregar/`, `paginas/administracion/`, `visor/`, `shell/carpetas/`; sus pruebas.

1. «Incidencia en el cambio (%)» en Actualizar precios y en la Hoja (donde diga «Aporte al cambio» o «Peso en el cambio»).
2. FCAS en la calculadora: la primera vez, «factor de costos asociados al salario (FCAS)».
3. Frentes (`PresupuestoPorFrentes.tsx`): «Ningún renglón tiene frente: póngalo abajo, o importe un Excel organizado por
   frentes.» → «Ninguna partida tiene frente de trabajo. Asígnelo con el selector de abajo o importe un Excel
   organizado por frentes.»; y el aviso de «salen del espacio de la obra … a mano» → «Las partidas creadas en la obra no
   tienen frente asignado. Para agruparlas, importe un Excel organizado por frentes.» Usa «partida», no «renglón».
4. Componer: «Los precios salen de la lista para armar de la carpeta, a la «Fecha de precios» de la composición.» →
   «Los precios salen de la lista de precios activa, en la «Fecha de precios» de este análisis.»; «La referencia MaPreX
   en bolívares» → «Referencia de precios MaPreX (en bolívares)».
5. AACE: quita la segunda frase cuando el precio SÍ está dentro del rango («Si queda fuera, revise…»); esa instrucción
   va solo en el mensaje de cuando queda fuera.
6. Mercado: «Primer cuartil (25 % más bajo)» → «Primer cuartil (el 25 % de los precios queda por debajo)».
7. Producción, reparto de cantera: «en partes iguales según las toneladas producidas» / «se divide en partes iguales por
   tonelada producida» → «en proporción a las toneladas producidas (el mismo costo por tonelada)».
8. Entregar y Empresa: aplica los dos nombres de «Código de verificación … (SHA-256)» de arriba; donde una ayuda hable de
   «clave pública», di «la clave de firma de su empresa».
9. Visor: «Escriba la fecha de auditoría antes de cargar el libro.» → «Escriba la fecha de la revisión antes de cargar el libro.»
10. Carpetas: «El archivo pasa de 20 MB.» (el aviso del navegador) → «El archivo pesa más de 20 MB, el máximo permitido.
    Redúzcalo o divídalo y vuelva a subirlo.» (el mensaje del servidor no lo toques).
11. Administración, respaldo: «Contraseña del respaldo cifrado (solo si el almacén seguro de contraseñas no está)» →
    rótulo «Contraseña del respaldo cifrado» con ayuda «Solo hace falta si su equipo no tiene almacén seguro de contraseñas».
