# Especialidad vial y de agregados: costo de producción propio, auditoría vial y proyección del riesgo

Fecha: 2026-10-30. Estado: descripción aprobada por Eugenio en conversación el 2026-10-30 («está perfecto, arma un
nuevo plan»); este documento la fija por escrito. La reorientación de la **tesis** a esta especialidad necesita el aval
del tutor; el **código** de este diseño no toca `core/` y no lo necesita.

Regla de datos (NORMAS y memoria del proyecto): ningún nombre de empresa, libro, costo ni cifra real entra al
repositorio. Todo caso del repositorio es ficticio; los datos reales viven solo en local (`data/`, ignorado).

## 1. Intención y por qué

Sílice se pensó para presupuestos de obra en general. Este diseño lo especializa en las empresas viales que
**producen su propio agregado pétreo y su mezcla asfáltica, pavimentan y demarcan vías**. Su problema no es armar APU
desde cero, sino lo que pasa **durante la obra**: los precios suben (cemento asfáltico, gasoil, tipo de cambio), cada
subida obliga a una reunión de reajuste con el dueño de la obra, y preparar cada reunión exige comparar precios a mano.

Este diseño especializa Sílice en esa cadena, que ningún programa revisado cubre:

    cantera → agregado propio → planta de asfalto → mezcla → colocación por tramo → demarcación

y la cierra con dos cosas que hoy no existen: **el costo propio de producción entra al APU con su origen**, y una
**proyección del riesgo de precios** que dice, con una probabilidad declarada, cuánto puede subir la obra y qué insumos
la empujan, para negociar una sola vez en vez de reaccionar a cada subida.

Por qué ahora: una tesis cercana de la misma escuela (sistema web de APU para obras civiles generales, con IA que arma
partidas) obliga a no competir en su terreno. La distancia viene de la **especialidad** (vial y agregados), del
**problema** (reajuste y riesgo durante la obra) y de la **evidencia medida**, no de añadir botones.

Éxito: que un presupuesto vial ficticio completo (tramos → cantidades → APU con costo propio de la mezcla → auditoría
vial → proyección del riesgo con su comprobación hacia atrás) corra de punta a punta en Sílice, con cada cifra
trazable a su origen, **sin un solo cambio en `core/`**.

## 2. Objetivos

1. **Especialidad vial.** Captura e importación de **tramos** (progresiva inicial y final, ancho, capas con su espesor
   y densidad compactada) que producen cantidades trazables (`ItemComputo` con `origen_id` = tramo y capa) para las
   partidas viales: fresado, base o sub-base granular, imprimación, riego de adherencia, carpeta asfáltica (m² y
   toneladas), bacheo, demarcación (línea continua y discontinua en metros, flechas y símbolos en m²) y transporte
   (t·km).
2. **Reglas viales del auditor.** Hallazgos con su tramo y su capa, al estilo de las reglas de `adapters/espacio/`:
   toneladas que no cuadran con área × espesor × densidad; porcentaje de asfalto fuera del rango de la fórmula de
   trabajo; dosis de riego (l/m²) fuera de rango; transporte que no cuadra con la distancia declarada; consumo de pintura
   por kilómetro fuera de rango; progresivas solapadas o con huecos; unidad incompatible con la partida. Todo rango es un
   parámetro con fuente (mismo criterio que `produccion/fuentes.py`: ninguna constante sin fuente).
3. **Costo de producción propio** en el gestor de producción, que hoy solo lleva cantidades:
   - **Costos del período**: gasoil, horas de equipo, nómina, mantenimiento, explosivos, energía y otros, con monto,
     moneda (Bs o USD), fecha, fuente y responsable. Nada se sobrescribe: una corrección es un registro nuevo.
   - **Receta de la planta**: una tonelada de mezcla consume agregados propios, cemento asfáltico y gasoil en las
     proporciones de su fórmula de trabajo (con fuente). Producir mezcla genera los consumos de sus componentes.
   - **Cálculo del costo por tonelada** de cada producto en un período: costos del período ÷ toneladas producidas, con
     una regla de reparto declarada entre productos; la mezcla suma el costo de sus componentes y el de la planta. Cada
     cálculo queda guardado con sus entradas (instantánea) y no se recalcula en silencio.
   - **Publicación al catálogo** como precio propio de la empresa (`crear_lista_de_empresa`, `PrecioPropio`) con fuente
     del tipo «Producción, período AAAA-MM, cálculo n.º N». El APU lo usa como cualquier precio y su origen se lee.
4. **Índices viales** para el reajuste y la proyección: series de cemento asfáltico, gasoil y las que hagan falta,
   importadas con `core/catalog/indices.registrar_importacion` (acepta cualquier código de serie; no hay que tocar el
   núcleo).
5. **Proyección del riesgo de precios** (método de las prácticas AACE 58R-10 y 68R-11, que se citan en la tesis):
   - Separa el **precio en dólares** del **efecto del tipo de cambio** (recomendación expresa de ambas prácticas).
   - Simula N trayectorias mensuales de cada serie a partir de su historia (ventana declarada), con **semilla fija y
     registrada**, y revaloriza el presupuesto en cada una con el motor de escenarios existente
     (`core/budget/escenarios.py`, que recalcula sin guardar nada).
   - Entrega: percentiles del costo total a la fecha de cada valuación prevista (al menos P50 y P80), la reserva que
     cubre el P80, y **qué insumos empujan más** la subida.
   - **Comprobación hacia atrás**: con un corte en una fecha pasada, proyecta y compara con lo que pasó; reporta la
     **cobertura** (cuántas veces la realidad cayó dentro del rango). Es la cifra que la tesis va a medir.
   - Determinista dada la semilla: la IA nunca calcula estos números.
6. **El asistente explica, no calcula.** Sobre los hallazgos viales y la proyección, el asistente redacta «qué
   desviaciones hay y qué riesgos se ven» citando los números que ya calculó el sistema (principio vigente: la IA
   nunca escribe un número final).
7. **Pantallas y reportes**: tramos de la obra; costos del período, recetas y costo por tonelada en el gestor de
   producción; «Riesgo de la obra» (proyección y comprobación hacia atrás); hallazgos viales en la bandeja. Reportes:
   cómputos por tramo, APU de la carpeta con el origen del costo propio, informe de riesgo.
8. **Ensayo de estrés.** Mutaciones viales en el sembrador de errores existente (`asistente/experimento/`): espesores,
   densidades, dosis, unidades y transcripciones alteradas, sobre copias **marcadas como prueba**. Sirve ahora para
   endurecer el sistema y después para la medición formal. Las copias de libros reales solo en local.
9. **Casos ficticios** en el repositorio: una vía ficticia con tramos, una cantera y una planta ficticias con costos e
   historia de índices inventada y declarada como tal.

## 2.1 Requisitos transversales que pide Eugenio (aprobación del 2026-10-30)

Eugenio aprobó este diseño con la condición de que el plan contemple estos puntos. Estado leído en el código el
2026-10-30 y lo que hace el plan con cada uno (sin tocar `core/`):

| Pedido | Estado hoy | Qué hace el plan |
|---|---|---|
| **Reportes** | Exportación a Excel de la hoja y del presupuesto (`aplicacion/hoja_exportar.py`), informe de revisión y de control | Reportes viales: cómputos por tramo, APU de la carpeta con el origen del costo propio, costo de producción por período, informe de riesgo, informe de mejora de la estimación y resumen del presupuesto con impuestos. Mismo mecanismo de exportación |
| **Escalabilidad, fácil ampliación y reducción del alcance** | Especialidades enchufables por contrato (`AdaptadorDominio`); módulos de navegación (`2026-10-25-modulos-design.md`) | **Especialidades y módulos activables por instalación**: el administrador enciende o apaga vial, edificación y producción; lo apagado no aparece en la interfaz y su API responde que no está disponible. Pruebas de arquitectura: nada de `core/` importa `adapters/vial` ni `produccion/`, y la aplicación arranca con lo vial apagado. Medida para la tesis: líneas cambiadas en `core/` al agregar lo vial (meta: cero) |
| **Multimoneda** | Bs y USD por proyecto, tasa BCV del día exacto, equivalencias con su rastro | Costos de producción, precios propios, proyección e informes en la moneda original con su equivalente y su tasa; nada nuevo en el núcleo |
| **Impuestos** | **El núcleo no calcula IVA** (`ParametrosCosto` solo tiene FCAS, bono, administración y utilidad) | **IVA sobre el total del presupuesto y de cada valuación** (subtotal, IVA, total), en `aplicacion/`, con la alícuota como parámetro con fuente y fecha; retenciones en la valuación solo si el plan confirma la norma. El APU no cambia |
| **Paro forzoso y utilidades** | FCAS es **un solo número** (6,00 por defecto, sin fuente normativa: deuda D4) | **Calculadora del FCAS por componentes** en `aplicacion/`: cada componente (entre ellos el paro forzoso, hoy Régimen Prestacional de Empleo, y las utilidades de los trabajadores) con su base legal, su cláusula de convención y su fecha; el resultado es el `fcas` que el núcleo ya recibe. Resuelve la D4 con fuentes. «Utilidad» de la empresa sigue siendo el parámetro existente. Los porcentajes de cada componente se cotejan con la norma antes de darlos por buenos |
| **Roles** | Arma, revisa y administrador, con acciones (`seguridad/permisos.py`, fuera del núcleo) | Acciones nuevas: registrar costos de producción, publicar costo propio, ver y correr la proyección, encender o apagar especialidades |
| **Tablas de búsqueda venezolanas** | Catálogo, MaPreX (julio 2026), tabulador CIV, tasa BCV; buscador global Ctrl+K; el autocompletado guiado en campos de datos está pedido y pendiente | **Búsqueda con autocompletado** en los campos viales y de producción: partidas viales, insumos (MaPreX y catálogo de la empresa), tasa BCV del día, salarios de la convención; cada sugerencia muestra su fuente |
| **Comprobación entre APU y presupuestos** | El auditor (R1–R15) revisa coherencia del presupuesto | **Conciliación** por partida: precio unitario del presupuesto contra el recalculado de su APU, cantidad del presupuesto contra la de los tramos, y costo propio usado contra el último publicado; cada diferencia es un hallazgo con su origen |
| **Estimación con valor final de mejora** | No existe | **Informe de mejora de la estimación**: para una obra culminada compara el costo final real con (a) el presupuesto original y (b) la estimación de Sílice con su reserva P80, y da el error de cada una y la mejora en puntos porcentuales. Es la cifra central de la tesis; con casos ficticios en el repositorio y datos reales solo en local |

## 3. No objetivos

- Diseño estructural de pavimentos (espesores por tránsito, AASHTO): Sílice presupuesta y audita, no diseña.
- Alineamientos o modelos 3D de vías (IFC de carreteras, LandXML).
- Contabilidad, nómina o inventario de repuestos: el gestor recibe costos ya totalizados por concepto y período.
- Descargar precios de internet o de proveedores automáticamente.
- Volver a hacer lo de edificaciones: los casos de edificación ya cargados quedan como **segunda especialidad de
  demostración**, sin trabajo nuevo.

## 4. Anti-objetivos (fracasos aunque «funcione»)

- **Tocar `core/`.** La tesis va a afirmar que agregar la especialidad no cambió el núcleo; un solo cambio lo
  desmiente. Criterio de aceptación: `git diff <base> -- core/` vacío al cerrar el plan.
- Prometer un precio exacto futuro. Solo rangos con probabilidad, y su acierto medido.
- Que la IA produzca una cifra de costo, de cantidad o de riesgo.
- Copiar como bandera lo que ya tiene la tesis cercana (armar APU con IA desde texto o foto, roles, Excel con firmas):
  puede existir, pero no es el aporte.
- Datos reales en el repositorio, aunque estén «anonimizados».

## 5. Decisiones tomadas

- **Especialidad vial = subespecialidad de civil.** `Dominio` es un enumerado cerrado en `core/contracts/dominio.py`;
  añadir `VIAL` tocaría el núcleo. Lo vial usa `Dominio.CIVIL` y se distingue con `especificaciones["especialidad"] =
  "vial"`, en un paquete propio `adapters/vial/`. (Decisión del orquestador, coherente con que la ingeniería vial es
  rama de la civil; la tesis declara como límite que un dominio fuera de los cuatro existentes sí exigiría tocar el
  contrato.)
- **El costo de producción se calcula en `produccion/`** (dominio puro: solo biblioteca estándar, `sqlalchemy`,
  `openpyxl`) y **se publica al catálogo desde `aplicacion/`**, que es la capa que ya conoce ambos. `produccion/` no
  importa `core/`.
- **La proyección vive fuera del núcleo** (`aplicacion/riesgo.py` o paquete `riesgo/`; lo decide el plan) y usa
  `core/budget/escenarios.py` y `core/catalog/indices.py` como bibliotecas.
- **Reglas viales en `adapters/vial/reglas.py`**, no en `core/verification/`.
- Moneda: cada costo y cada precio guarda su moneda original, fecha y fuente; la conversión usa la tasa BCV **del día
  exacto** (decisión vigente de Eugenio del 2026-10-27).
- Números: coma decimal y punto de miles en toda entrada y salida (decisión de Eugenio del 2026-10-25).
- TDD en todo lo nuevo y suite completa al cerrar (regla vigente del 2026-10-18). Agentes uno a la vez, cada tarea con
  su árbitro; el navegador solo al final.

### 5.1 Decisiones del orquestador tras la revisión del diseño (2026-10-30)

Un revisor independiente leyó este documento contra el código. Ninguna de sus preguntas necesitaba a Eugenio; estas
son las respuestas, marcadas como decisión del orquestador (Eugenio puede cambiarlas):

1. **Fechas de la proyección.** `core/budget/curva.py` reparte por «Día N», sin fechas, así que no sirve como
   calendario. La proyección toma su horizonte así: si la obra tiene línea base con calendario
   (`core/budget/valuaciones.py`: `Calendario`, `LineaBase`), usa sus fechas de corte; si no, la persona declara en la
   pantalla la fecha de inicio, el plazo en meses y la periodicidad (mensual por defecto). El reparto del gasto en
   el tiempo es uniforme por defecto, declarado como supuesto.
2. **La mezcla se recalcula en cada trayectoria.** Revalorizar no es solo cambiar el precio del cemento asfáltico: en
   cada trayectoria se recalcula primero el costo propio (receta × precios simulados de sus componentes + costo de
   planta) y ese costo entra como precio del insumo «mezcla propia». Si no se hiciera, el riesgo quedaría subestimado.
   Cada serie se enlaza con sus insumos mediante un mapa declarado (serie → códigos de insumo), guardado con la
   proyección.
3. **Moneda en la simulación.** La tasa BCV se simula como una serie más y **junto con las demás**: se remuestrean
   meses históricos completos (todas las series del mismo mes a la vez), lo que conserva su correlación. Un insumo con
   precio en Bs y sin serie propia se trata como «USD fijo × tasa simulada» (supuesto declarado en el informe).
4. **Cobertura.** La comprobación hacia atrás corre sobre **cortes móviles** mensuales a lo largo de toda la historia
   disponible, con horizonte configurable (6 meses por defecto), y reporta la cobertura y el número de cortes usados.
   Con los casos ficticios solo se prueba la mecánica; la cobertura que va a la tesis se calcula con datos reales en
   local.
5. **Ensayo de estrés.** El sembrador actual está atado a `Espacio` (`asistente/experimento/mutaciones.py`). Lo vial
   tendrá un **sembrador paralelo** (`asistente/experimento/mutaciones_viales.py` o similar) que reutiliza el banco, el
   congelado y el comparador donde se pueda, sin cambiar el comportamiento del sembrador de `Espacio`.
6. **Publicación al catálogo.** Cada cálculo publicado crea una lista de empresa nueva (comportamiento actual de
   `crear_lista_de_empresa`: alcance `empresa`, la versión la referencia explícitamente). El insumo «agregado propio X»
   y «mezcla propia Y» se da de alta en el catálogo desde `aplicacion/` la primera vez que se publica, con el código
   del material del gestor; cada `PrecioPropio` conserva su moneda original, fecha y fuente.
7. **Series.** `core/catalog/indices._serie` rechaza que una serie existente cambie de unidad o periodicidad: las
   series viales se definen una vez con su unidad y periodicidad y las reimportaciones las respetan.

## 6. Lo que queda al constructor

- La forma exacta de las tablas nuevas del gestor (`prod_costo`, receta y cálculo) y su migración.
- El formato del archivo de tramos (CSV o xlsx) y el de importación de costos del período.
- La regla de reparto **por defecto** de los costos de la cantera entre productos (proponer y declarar; Eugenio puede
  cambiarla).
- El método de muestreo de la proyección (remuestreo de variaciones mensuales históricas o distribución ajustada),
  siempre que sea reproducible con la semilla y quede documentado con su fuente.
- Los rangos por defecto de las reglas viales, cada uno con su fuente o marcado para cotejar antes de usarse en la
  medición.
- El orden de las tareas, con una condición: **el registro de costos del período va primero**, porque los datos reales
  solo existen desde que la empresa empiece a registrarlos.

## 7. Riesgos

- **Historia de precios del cemento asfáltico**: puede no existir una serie pública. Si falta, la proyección se apoya en
  la tasa BCV, el gasoil y lo que la empresa haya registrado, y la tesis lo declara.
- **Costos reales de cantera y planta**: dependen de que la empresa los entregue o empiece a registrarlos.
- **Datos reales (revisados en local el 2026-10-30).** Los presupuestos reales disponibles son de **edificación**
  (rehabilitación de frisos y paredes), en versión definitiva y **sin obra terminada**; uno está en ejecución. Usan
  agregados como insumo (arena lavada, arena amarilla, polvillo), con poco peso en el costo. **No hay todavía
  presupuestos viales ni de obras con piedra picada**: Eugenio los añadirá pronto. Consecuencia: la fase A (costo de
  producción) y las pruebas de errores, tiempo y comprobación hacia atrás no dependen de ellos; lo vial se construye
  y se prueba con casos ficticios hasta que lleguen. El inventario real vive solo fuera del repositorio.
