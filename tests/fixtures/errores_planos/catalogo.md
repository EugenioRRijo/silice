# Catálogo de errores sembrados en planos (S3 §11.5, RF-89)

Se escribe en S3-0, **antes** del código de R15 y R16. Cada bloque dice qué se siembra, cómo y
qué detección se espera. `scripts/sembrar_errores_planos.py` implementa una siembra por `id` y la
prueba `tests/unit/test_deteccion_planos.py` vigila que los dos conjuntos de `id` coincidan.

## Lenguaje de las detecciones

Cada campo *Detección esperada* y *Consecuencias admitidas* lleva una o más etiquetas separadas
por `;`; una etiqueta puede unir alternativas con `|` (se cumple si se cumple alguna). Frente al
plano limpio, la auditoría AGREGA:

- `estado:<valor>`: el estado de la importación es `<valor>` (`detenida`, `rechazada`);
- `item:<tipo>:<texto>`: un ítem del informe de importación de ese tipo cuyo mensaje contiene
  `<texto>`;
- `regla:<R>:<texto>`: un hallazgo de esa regla (`R8`, `R9`, `R10`, `R15`) cuya descripción
  contiene `<texto>`;
- `r16:<tipo>`: una diferencia de R16 de ese tipo (`faltante`, `sobrante`, `desplazado`) entre el
  plano sembrado y el limpio;
- `ninguna`: nada; es un control no detectable (mide el límite declarado).

Las *consecuencias admitidas* son agregados que el error provoca por fuerza (la escala ×1000
agranda todos los recorridos); lo que se agregue y no esté ni en la detección ni en las
consecuencias es una **falsa alarma**. Lo que el plano limpio ya tenía (sus 15 ítems y sus 8
hallazgos de R8, ver `of001_limpio.py`) no se cuenta.

**Autor.** `P`: lo escribió el ingeniero de pruebas sin ver la implementación de R15 ni de R16
(§13.5 b); `A`: lo escribió quien programa los adaptadores.

Los tres controles **no detectables** miden el límite declarado de la auditoría de planos: sin una
segunda fuente, un plano coherente pero equivocado no se distingue de uno correcto (H-D9). Se
informan con su número; no entran en la tasa de detección ni en las falsas alarmas.

## Errores

### SIN-UNIDAD

- **Categoría:** sin `$INSUNITS`
- **Cómo se siembra:** se borra la unidad del encabezado del DXF
- **Detección esperada:** estado:detenida
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### ENTIDAD-DANADA

- **Categoría:** entidad dañada
- **Cómo se siembra:** una línea con un tipo de línea que no existe
- **Detección esperada:** item:aproximado:error de estructura
- **Consecuencias admitidas:** item:no reconocido:fuera de la convencion
- **Detectable:** sí
- **Autor:** P

### CAPA-EQUIVOCADA

- **Categoría:** bloque en capa equivocada
- **Cómo se siembra:** un punto de datos pasa a la capa `PTO-DATO` (errata)
- **Detección esperada:** item:no reconocido:fuera de la convencion
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### ALTURA-FALTANTE

- **Categoría:** `ALTURA` faltante
- **Cómo se siembra:** a un punto se le quita el atributo `ALTURA`
- **Detección esperada:** item:pendiente:sin atributo ALTURA
- **Consecuencias admitidas:** regla:R8:altura pendiente
- **Detectable:** sí
- **Autor:** P

### ESCALA-X1000

- **Categoría:** escala ×1000
- **Cómo se siembra:** todo el dibujo se multiplica por 1000 con la unidad en metros
- **Detección esperada:** regla:R15:escala imposible
- **Consecuencias admitidas:** regla:R15:de su fuente; regla:R10:enlace de
- **Detectable:** sí
- **Autor:** P

### SUPERPUESTO

- **Categoría:** ambiente superpuesto
- **Cómo se siembra:** un ambiente nuevo que pisa 0,25 m² de ZA y 0,75 m² de ZB
- **Detección esperada:** regla:R15:se superponen
- **Consecuencias admitidas:** item:pendiente:altura pendiente; regla:R8:altura pendiente;
  item:aproximado:cae en varios ambientes
- **Detectable:** sí
- **Autor:** P

### PUNTO-DUPLICADO

- **Categoría:** punto duplicado
- **Cómo se siembra:** un punto de datos se copia sobre sí mismo con otro id
- **Detección esperada:** regla:R15:duplicados
- **Consecuencias admitidas:** item:aproximado:fuente
- **Detectable:** sí
- **Autor:** P

### FUERA-DE-AMBIENTE

- **Categoría:** punto fuera de todo ambiente
- **Cómo se siembra:** un punto de datos se lleva a (30; 30)
- **Detección esperada:** item:no reconocido:queda fuera de todo ambiente
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### SIN-FUENTE

- **Categoría:** punto sin fuente
- **Cómo se siembra:** se borra el rack de datos o el tablero
- **Detección esperada:** item:pendiente:sin fuente compatible|item:pendiente:sin tablero
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-ALTURA

- **Categoría:** `IfcSpace` sin altura
- **Cómo se siembra:** el IFC de oficina sin `Qto_SpaceBaseQuantities.Height`
- **Detección esperada:** item:pendiente:IDS «Espacio con altura»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-DIAMETRO

- **Categoría:** aparato sin diámetro
- **Cómo se siembra:** el IFC de oficina sin `Silice_Hoja.DiametroNominal`
- **Detección esperada:** item:pendiente:IDS «Aparato sanitario con diametro»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-CIRCUITO

- **Categoría:** tomacorriente sin circuito
- **Cómo se siembra:** el IFC de oficina sin `Silice_Hoja.Circuito`
- **Detección esperada:** item:pendiente:IDS «Tomacorriente con circuito»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### ELEMENTO-BORRADO

- **Categoría:** elemento borrado entre dos fuentes
- **Cómo se siembra:** el plano pierde un punto que el levantamiento sí trae
- **Detección esperada:** r16:faltante
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### DESPLAZADO-0-50

- **Categoría:** punto desplazado 0,50 m entre dos fuentes
- **Cómo se siembra:** un punto se corre 0,50 m hacia el interior de su ambiente
- **Detección esperada:** r16:desplazado
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### NO-DET-TRASLADO

- **Categoría:** control: todo el plano trasladado
- **Cómo se siembra:** todo el dibujo se corre 0,50 m en x (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P

### NO-DET-PERMUTA

- **Categoría:** control: dos puntos con los ids cambiados
- **Cómo se siembra:** `PA1` y `PA2` intercambian sus ids (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P

### NO-DET-LUCES

- **Categoría:** control: luminarias corridas
- **Cómo se siembra:** las cuatro luminarias se corren 0,30 m en y (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P
