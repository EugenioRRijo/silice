# Plan de desarrollo con Claude Code

Sistema de generación y auditoría de Análisis de Precios Unitarios multidominio.

Este plan traduce los siete incrementos del plan de implementación a sesiones concretas de trabajo. Cada sesión tiene objetivo, prompt sugerido, criterio de cierre y commit esperado.

> **Errata (2026‑09‑15).** Este plan llamaba «reales» a los cinco APU y al presupuesto auditado del
> caso de la clínica. Son un **ejercicio académico ficticio**: la línea base normativa de las
> pruebas y un caso didáctico en la tesis. El texto quedó corregido en la sesión de limpieza; la
> fuente única de la naturaleza de los datos es [CLAUDE.md §1](CLAUDE.md#1-qué-es-este-proyecto).

---

## Antes de empezar

### Preparación del entorno

```bash
mkdir apu_system && cd apu_system
git init
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install sqlalchemy pandas pytest ruff
```

Copiar `CLAUDE.md` a la raíz del repositorio. Es lo primero, antes de cualquier código.

```bash
claude
```

### Cómo trabajar en cada sesión

| Práctica | Por qué |
|---|---|
| Usar modo plan antes de cambios grandes (Shift+Tab) | Ver la propuesta antes de que escriba archivos |
| Una sesión por incremento, `/clear` entre ellas | El contexto acumulado degrada la calidad |
| Una rama por incremento | `git checkout -b inc/I1-actualizacion-precios` |
| Pedir pruebas antes que implementación en `core/costing` | Hay línea base verificada contra la cual medir |
| Revisar cada diff antes de aceptar | El código lo defiendes tú, no Claude |

### Regla que evita el 80 % de los problemas

Si Claude propone modificar algo dentro de `core/` mientras trabajas en un adaptador, **detenerse**. O el adaptador está mal diseñado, o el contrato de interfaz es insuficiente. Ambas cosas son hallazgos de la investigación y deben documentarse, no parchearse.

---

## Fase 0. Documentación previa

Sin código todavía. Estas sesiones producen los entregables que el jurado de sistemas evalúa.

### Sesión 0.1 — Requerimientos

**Objetivo.** Convertir los ocho casos de uso en requerimientos funcionales numerados.

```
Lee CLAUDE.md. Necesito redactar la Especificación de Requerimientos
de Software bajo IEEE 830 para este sistema.

Los ocho casos de uso son:
UC-01 Elaborar presupuesto nuevo desde una fuente de cantidades
UC-02 Actualizar masivamente los precios de un presupuesto existente
UC-03 Reutilizar partidas y desgloses de proyectos anteriores
UC-04 Recalcular ante cambio de alcance o dimensiones
UC-05 Auditar un presupuesto elaborado por un tercero
UC-06 Registrar y consultar rendimientos reales de obra ejecutada
UC-07 Contrastar el precio construido con el precio de mercado
UC-08 Generar escenarios de sensibilidad

Genera docs/ERS.md con la estructura completa de IEEE 830.
Deriva los requerimientos funcionales de los casos de uso, numerados
RF-01 en adelante, cada uno con prioridad y trazabilidad al caso de uso
que lo origina. Incluye requerimientos no funcionales agrupados por las
características de ISO/IEC 25010 pertinentes.

No escribas código.
```

**Cierre.** `docs/ERS.md` con al menos 20 RF numerados y su matriz de trazabilidad.
**Commit.** `docs(ers): especificacion de requerimientos IEEE 830`

---

### Sesión 0.2 — Modelo de datos

**Objetivo.** El esquema de base de datos. Es el paso más importante de toda la fase 0, porque el modelo de datos materializa el contrato de interfaz.

```
Diseña el modelo de datos del sistema. Entidades mínimas que debe cubrir:

- Partida (código, descripción, unidad, dominio)
- Insumo (material, equipo o mano de obra, con precio y fecha de vigencia)
- ComposicionAPU (relación partida-insumo con cantidad y factor de depreciación)
- Rendimiento (partida, valor, condiciones, fecha, si proviene de ejecución real)
- Proyecto, Presupuesto, PartidaPresupuestada
- ItemComputo persistido, con origen_id y origen_tipo
- ListaPrecios y su historial de cambios

Requisitos:
- El histórico de precios debe permitir reconstruir cualquier presupuesto
  a la fecha en que se elaboró.
- Rendimiento debe distinguir valor estimado de valor medido en ejecución.
- Usa Decimal para todo lo monetario.

Genera docs/modelo_datos.md con el diagrama entidad-relación en Mermaid,
la descripción de cada entidad y la justificación de la normalización.
Todavía no escribas los modelos SQLAlchemy.
```

**Cierre.** Diagrama ER que soporte los ocho casos de uso.
**Commit.** `docs(datos): modelo entidad-relacion`

---

### Sesión 0.3 — Arquitectura

```
Genera docs/arquitectura.md documentando el sistema con las vistas 4+1
de Kruchten. Incluye en Mermaid:

- Vista de casos de uso: diagrama de casos de uso con los actores
- Vista lógica: diagrama de clases de core/ y del contrato de adaptadores
- Vista de proceso: diagramas de secuencia de UC-02 y UC-05
- Vista de desarrollo: diagrama de componentes que muestre el núcleo,
  los cuatro adaptadores y las interfaces provistas y requeridas
- Vista física: diagrama de despliegue

El diagrama de componentes es el más importante. Debe hacer evidente
que agregar un adaptador no toca el núcleo.
```

**Cierre.** Cinco vistas documentadas.
**Commit.** `docs(arq): vistas 4+1 y diagramas UML`

---

## Fase 1. Núcleo

### Sesión I0.1 — Contratos y esqueleto

```
Crea la estructura de carpetas descrita en CLAUDE.md sección 6, con
__init__.py donde corresponda, pyproject.toml con las dependencias
y configuración de ruff y pytest.

Implementa core/contracts/ exactamente como está especificado en
CLAUDE.md sección 5. Estos archivos son estables, no deben cambiar
en el resto del proyecto.

Nada más por ahora.
```

**Commit.** `feat(core): contratos de interfaz y estructura del proyecto`

---

### Sesión I0.2 — Pruebas del motor de costos

Esta sesión va **antes** de implementar el motor. Es deliberado.

```
Lee la sección 4 de CLAUDE.md, que contiene la especificación exacta
del cálculo y los cinco APU verificados de la línea base.

Crea tests/fixtures/apu_linea_base.py con los cinco casos como datos
de prueba, y tests/unit/test_costing.py con las pruebas que verifiquen
que el motor produce el precio unitario esperado en cada caso, con
tolerancia de 0.01.

Incluye pruebas específicas para los dos errores más probables:
1. Que los materiales NO se dividan entre el rendimiento
2. Que administración y utilidad se apliquen en cascada y no sumadas

Las pruebas deben fallar ahora, porque el motor no existe.
```

**Cierre.** `pytest` falla con cinco errores de importación. Eso es correcto.
**Commit.** `test(core): fixtures de linea base y pruebas del motor`

---

### Sesión I0.3 — Motor de costos

```
Implementa core/costing/ para que pasen todas las pruebas de
tests/unit/test_costing.py. No modifiques las pruebas.

Usa Decimal en todo el cálculo. Que el motor sea una función pura,
sin acceso a base de datos.

Cuando pasen las cinco, muéstrame el resultado de pytest.
```

**Cierre.** Cinco pruebas en verde.
**Commit.** `feat(core): motor de costos con prestaciones, bono y depreciacion`

---

### Sesión I0.4 — Persistencia

```
Implementa core/models/ con SQLAlchemy siguiendo docs/modelo_datos.md,
y core/catalog/ con las operaciones de consulta y carga de partidas,
insumos y rendimientos.

Agrega un script scripts/seed.py que cargue los cinco APU de la línea
base en la base de datos, de modo que se pueda reproducir el presupuesto
completo desde SQLite.

Pruebas de integración en tests/integration/.
```

**Commit.** `feat(core): persistencia y catalogo de partidas`

---

### Sesión I0.5 — Presupuesto y curva

```
Implementa core/budget/ que a partir de una lista de ItemComputo y del
catálogo genere el presupuesto completo y la curva de inversión.

La curva debe cerrar exactamente en el total del presupuesto. Escribe
una prueba que lo verifique, porque en el presupuesto auditado
cerraba en 99.30 % y esa es una de las siete inconsistencias que el
sistema debe evitar por construcción.

Exportación a Excel con openpyxl.
```

**Cierre.** Presupuesto reproducido y curva que cierra al 100 %.
**Commit.** `feat(core): presupuesto y curva de inversion`

---

## Fase 2. Valor percibido

Aquí empieza lo que un profesional usaría. Corresponde al principio rector del plan, entregar primero lo que el usuario sí padece.

### Sesión I1 — Actualización masiva de precios (UC-02)

```
Implementa UC-02. El usuario carga una lista de precios actualizada
(CSV o Excel) y el sistema:

1. Identifica los insumos afectados
2. Recalcula todos los APU del proyecto
3. Registra qué cambió, en qué proporción y con qué incidencia por partida
4. Genera un informe comparativo entre versión anterior y nueva

El registro de cambios debe persistirse, porque constituye el histórico
de precios que después alimentará el módulo predictivo.

Interfaz mínima en Streamlit para cargar el archivo y ver el informe.
```

**Cierre.** Cargar una lista y ver el presupuesto actualizado con el comparativo.
**Commit.** `feat(core): actualizacion masiva de precios con registro de cambios`

> Al cerrar esta sesión ya existe algo que un profesional instalaría, sin una sola línea de inteligencia artificial. Vale la pena registrarlo como hito en la tesis.

---

### Sesión I2 — Memoria y normalización (UC-03)

```
Implementa ml/normalization/ usando sentence-transformers con el modelo
paraphrase-multilingual-MiniLM-L12-v2.

Función: dada una descripción de partida en texto libre, devolver las
tres partidas más similares del catálogo con su puntaje de similitud
del coseno.

Importante: este módulo NO requiere datos etiquetados ni entrenamiento.
Funciona por similitud semántica directa.

Integrar en el flujo de creación de partidas, de modo que al escribir
una descripción el sistema proponga coincidencias del histórico con su
desglose y su rendimiento.

Prueba de aceptación: sobre un presupuesto conocido debe reconocer
correctamente al menos el 80 % de las partidas.
```

**Commit.** `feat(ml): normalizacion semantica de partidas`

---

## Fase 3. Adaptador civil y verificación

### Sesión I3.1 — Extracción IFC (prueba de concepto)

Antes de esta sesión, modelar en Revit o Bonsai una sola tanquilla y exportarla a IFC.

```
Implementa adapters/civil/ como AdaptadorDominio usando ifcopenshell.

Debe leer un archivo IFC, recorrer los elementos, obtener sus cantidades
geométricas (IfcElementQuantity) y el conjunto de propiedades
personalizado Pset_APU con los campos COVENIN_Codigo, Partida_Descripcion
y Unidad, y devolver una lista de ItemComputo con origen_id igual al
GlobalId del elemento IFC.

Empieza probando con data/samples/tanquilla.ifc, que tiene un solo
elemento.
```

**Compuerta G1.** Si las cantidades extraídas no coinciden con el cálculo manual, el adaptador civil se sustituye por entrada tabular y se documenta. El resto del sistema no se ve afectado.

**Commit.** `feat(civil): adaptador IFC con extraccion de cantidades`

---

### Sesión I3.2 — Motor paramétrico (UC-04)

```
Implementa las reglas paramétricas del dominio civil en
adapters/civil/reglas.py, con la especificación siguiente para una
tanquilla de ancho exterior a, altura h y espesor de pared e:

  concreto   = (a**2 - (a - 2*e)**2) * h
  encofrado  = 4*a*h + 4*(a - 2*e)*h
  excavacion = (a + 2*sobreancho)**2 * (h + espesor_fondo)
  relleno    = excavacion_total - volumen_concreto - volumen_tuberia

Cada regla debe quedar registrada como expresión trazable, de modo que
el informe pueda mostrar de qué regla salió cada cantidad.

Prueba: con a=0.80, h=0.80, e=0.10 el concreto debe dar 0.224 m3 y el
encofrado 4.48 m2. En el presupuesto auditado se usaron 0.415 y
5.92 respectivamente, que son dos de las siete inconsistencias.
```

**Commit.** `feat(civil): motor de reglas parametricas trazables`

---

### Sesión I4 — Verificación (UC-05)

```
Implementa core/verification/ con las siete reglas de la sección 7 de
CLAUDE.md.

Cada regla es una clase con un método evaluar() que devuelve una lista
de hallazgos, cada uno con severidad, descripción, cuantificación del
impacto y referencia al origen_id involucrado.

El informe de auditoría se genera siempre, sin que el usuario lo solicite.

Prueba de aceptación crítica: crear en tests/fixtures un presupuesto que
reproduzca las siete inconsistencias del caso didáctico auditado, y verificar
que el sistema las detecta todas.
```

**Cierre.** Siete de siete detectadas. Es el indicador 1 de la tesis.
**Commit.** `feat(core): sistema de verificacion de consistencia`

---

## Fase 4. Extensibilidad

### Sesión I5 — Los otros tres adaptadores

```
Implementa adapters/telecom/, adapters/industrial/ y adapters/sistemas/.

Cada uno lee su fuente propia y devuelve ItemComputo:
- telecom: topología de red en CSV (nodos, enlaces, longitudes)
- industrial: registro de activos con frecuencia de intervención
- sistemas: alcance funcional (módulos, casos de uso, puntos de función)

REGLA CRÍTICA: no modifiques nada dentro de core/. Si algo parece
requerirlo, detente y explícame por qué, sin escribir el cambio.
Esa situación es un hallazgo de la investigación.

Al terminar, ejecuta git diff --stat core/ y muéstrame el resultado.
```

**Cierre.** `git diff --stat core/` vacío. Es la prueba empírica de la hipótesis central y el indicador 4 de la tesis.
**Commit.** `feat(adapters): telecom, industrial y sistemas sin modificar el nucleo`

---

## Fase 5. Inteligencia artificial

### Sesión I6.1 — Detección de anomalías

```
Implementa ml/anomaly/ con Isolation Forest de scikit-learn.

Dos usos:
1. Precios unitarios que se apartan del histórico
2. Rendimientos que se apartan de lo observado en ejecución real

No requiere datos etiquetados. Entrena sobre el histórico acumulado.
```

**Commit.** `feat(ml): deteccion de anomalias en precios y rendimientos`

---

### Sesión I6.2 — Rendimientos auditables (UC-06)

```
Implementa el registro de rendimientos reales, que es el aporte de mayor
valor del trabajo.

- Registrar rendimiento efectivo con partida, condiciones, fecha y
  referencia a la ejecución
- Al crear un APU, proponer el rendimiento del histórico y mostrar su
  dispersión
- Advertir cuando el valor introducido se aparta del comportamiento
  observado
- Distinguir siempre rendimiento estimado de rendimiento medido
```

**Commit.** `feat(core): rendimientos auditables con trazabilidad a ejecucion`

---

### Sesión I6.3 — Predicción de precio (UC-07)

**Compuerta G2.** Antes de esta sesión, contar los registros disponibles.

| Registros por dominio | Acción |
|---|---|
| Más de 200 | XGBoost según lo previsto |
| Entre 50 y 200 | Razonamiento basado en casos con validación dejando uno fuera |
| Menos de 50 | Sistema de reglas con análisis de sensibilidad, declarado como limitación |

```
Tengo N registros por dominio. Según el criterio de degradación de la
sección 8.1 del plan, implementa la técnica que corresponde en
ml/prediction/.

Reporta MAPE, RMSE y R2. Genera docs/resultados_ml.md con las métricas
y la comparación entre técnicas.
```

**Commit.** `feat(ml): prediccion de precio unitario y metricas`

---

## Fase 6. Cierre

### Sesión F.1 — Interfaz completa y API

```
Completa ui/app.py en Streamlit con los ocho casos de uso, y api/main.py
en FastAPI exponiendo las operaciones del núcleo.

FastAPI genera documentación OpenAPI automática. Exporta el esquema a
docs/api.json, que es documentación entregable sin esfuerzo adicional.
```

**Commit.** `feat(ui): interfaz completa y API documentada`

---

### Sesión F.2 — Plan de pruebas y calidad

```
Genera docs/plan_pruebas.md bajo IEEE 829, con casos de prueba
trazados a cada requerimiento funcional de la ERS.

Genera también docs/calidad_iso25010.md evaluando el sistema en
adecuación funcional, usabilidad, mantenibilidad y fiabilidad, con
métricas concretas.

Ejecuta pytest con cobertura y reporta el resultado.
```

**Commit.** `docs(test): plan de pruebas IEEE 829 y evaluacion ISO 25010`

---

### Sesión F.3 — Manuales

```
Genera docs/manual_usuario.md y docs/manual_tecnico.md.

El manual técnico debe incluir la guía para escribir un adaptador nuevo,
porque la extensibilidad es el aporte del trabajo y debe quedar
documentada de forma que un tercero pueda ejercerla.
```

**Commit.** `docs: manuales de usuario y tecnico`

---

## Resumen del recorrido

| Fase | Sesiones | Producto | Semanas del plan |
|---|---|---|---|
| 0. Documentación | 3 | ERS, modelo de datos, arquitectura | 3 a 8 |
| 1. Núcleo | 5 | Motor de costos, persistencia, presupuesto | 8 a 11 |
| 2. Valor percibido | 2 | Actualización de precios, memoria | 11 a 16 |
| 3. Civil y verificación | 3 | Adaptador IFC, paramétrico, auditoría | 16 a 21 |
| 4. Extensibilidad | 1 | Tres adaptadores más | 21 a 24 |
| 5. Inteligencia artificial | 3 | Anomalías, rendimientos, predicción | 24 a 26 |
| 6. Cierre | 3 | Interfaz, pruebas, manuales | 26 a 28 |

Total, 20 sesiones de trabajo.

---

## Los tres momentos que definen el trabajo

**Sesión I0.3.** Cuando pasen las cinco pruebas del motor de costos, el núcleo está validado contra la línea base auditada. Todo lo demás se construye encima con confianza.

**Sesión I3.1, compuerta G1.** Si la extracción IFC falla, se sabe en la semana 19, con los incrementos I0, I1 e I2 ya entregados y nueve semanas por delante. Nunca se pierde el trabajo.

**Sesión I5.** El comando `git diff --stat core/` devolviendo vacío es la prueba empírica de la hipótesis central. Ese resultado es la tesis.

---

## Continuación

Este plan se completó el 2026‑08‑31 (20 de 20 sesiones). Su continuación — poblar los dominios
telecom, industrial y sistemas con catálogos, presupuestos auditados y precios publicados de la
fuente natural de cada ingeniería — está en [PLAN_MULTIDOMINIO.md](PLAN_MULTIDOMINIO.md).
