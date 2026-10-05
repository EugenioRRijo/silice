# Memoria de cálculo a mano: baño de OF-001 (agua fría)

Oráculo de las tareas 1.2 a 1.5 del sprint final (spec §6.4, §6.5, §7.1, §11.2). Está hecha a mano, con
aritmética exacta (`Decimal`), y **no depende de ningún código del proyecto**. Las pruebas de
`adapters/espacio` comparan contra este archivo a ±0,001 m, no contra la expresión de la regla R1.

**Naturaleza de los datos** (NORMAS.md §1). OF-001 es un caso construido para el proyecto. Las
coordenadas de este baño son **supuestos declarados** (números simples para poder contar a mano); no
provienen de un plano ni de una obra ejecutada. Origen de medida de todas las filas: tipo *Supuesto*,
motivo «ejemplo de memoria de cálculo».

**Alcance: solo agua fría.** El drenaje queda para la tarea 1.5 con su propia memoria. Motivo: spec §7.1
no da reglas de derivación del drenaje con precisión suficiente para un oráculo a mano (la pendiente
mínima es la constante de R10, cuya fuente, Gaceta Oficial N.º 4.044 Extraordinario de 1988, no está
verificada: bitácora SF, tarea 0.4, RS-5), y un oráculo con una pendiente inventada sería circular. El
recorrido de drenaje de §6.4 (baja al piso, recorre en x y y, z decreciente) se detallará allí con la
pendiente como supuesto declarado.

Unidades: metros. Eje z hacia arriba desde el piso terminado. Tolerancia geométrica: 0,001 m.

## 1. Modelo espacial de ejemplo

| Tabla | Fila | Datos |
|---|---|---|
| Ambiente | `BAN-01` | x0 = 0,000; y0 = 0,000; largo (x) = 2,000; ancho (y) = 1,500; alto = 2,500 |
| Fuente | `F1` | agua fría, montante de agua, ambiente `BAN-01`, (x, y, z) = (0,000; 0,000; 0,000) |
| Punto | `P1` | lavamanos, agua fría, pared, (1,500; 0,000; 0,600), fuente `F1`, diámetro 1/2", declara llave de paso |
| Punto | `P2` | ducha, agua fría, pared, (1,000; 1,500; 1,200), fuente `F1`, diámetro 3/4", declara llave de paso |

Dentro del ambiente: 0 ≤ x ≤ 2,000; 0 ≤ y ≤ 1,500; 0 ≤ z ≤ 2,500. Cada punto está **sobre un muro**: `P1` en
el muro y = 0 y `P2` en el muro y = 1,5; la montante `F1` está en la esquina (0; 0). Por eso todas las
bajantes (S1, S4, S6) corren por muro y es coherente contarlas como empotradas.
El techo está en z = alto = 2,500.

## 2. Recorrido propuesto de cada punto (spec §6.4, agua fría)

Regla: desde la fuente sube al techo, recorre en x y luego en y por el techo, y baja por la pared hasta la
altura del punto. Un tramo de largo cero (por ejemplo, recorrer en y cuando y no cambia) **se omite**.

**Recorrido de `P1`** (vértices): A(0; 0; 0) → B(0; 0; 2,5) → C(1,5; 0; 2,5) → D(1,5; 0; 0,6)

| Tramo | De → a | Superficie | Cálculo | Longitud (m) |
|---|---|---|---|---|
| P1-1 | A → B (sube) | pared | 2,5 − 0 | 2,500 |
| P1-2 | B → C (en x, techo) | techo | 1,5 − 0 | 1,500 |
| (en y) | C → C | techo | 0 − 0, omitido | 0 |
| P1-3 | C → D (baja) | pared | 2,5 − 0,6 | 1,900 |

Longitud del recorrido de `P1`: 2,5 + 1,5 + 1,9 = **5,900 m**.

**Recorrido de `P2`** (vértices): A(0; 0; 0) → B(0; 0; 2,5) → E(1; 0; 2,5) → G(1; 1,5; 2,5) → H(1; 1,5; 1,2)

| Tramo | De → a | Superficie | Cálculo | Longitud (m) |
|---|---|---|---|---|
| P2-1 | A → B (sube) | pared | 2,5 − 0 | 2,500 |
| P2-2 | B → E (en x, techo) | techo | 1 − 0 | 1,000 |
| P2-3 | E → G (en y, techo) | techo | 1,5 − 0 | 1,500 |
| P2-4 | G → H (baja) | pared | 2,5 − 1,2 | 1,300 |

Longitud del recorrido de `P2`: 2,5 + 1,0 + 1,5 + 1,3 = **6,300 m**.

Suma de recorridos **sin unir**: 5,900 + 6,300 = 12,200 m. Esa suma **no** es la tubería: contaría dos veces
los tramos compartidos.

## 3. Unión de segmentos (spec §6.5) y solape parcial colineal

Los dos recorridos forman un árbol con raíz en `F1`:

- P1-1 y P2-1 son el mismo segmento (A → B), coincidencia total.
- P1-2 recorre en x de 0 a 1,5 sobre la recta (y = 0, z = 2,5); P2-2 recorre esa misma recta de 0 a 1,0. Es
  un **solape parcial colineal**: P2-2 queda contenido en la primera parte de P1-2. La geometría parte
  P1-2 en el nodo E(1; 0; 2,5): `[0; 1]` (compartido) y `[1; 1,5]` (solo de `P1`).

Segmentos únicos tras la partición (clave = extremos a 0,001 m, en orden lexicográfico, más la fuente):

| Seg. | Extremos | Longitud (m) | Sirve a | Diámetro (mayor de los que sirve) | Empotrado |
|---|---|---|---|---|---|
| S1 | (0;0;0) – (0;0;2,5) | 2,500 | P1, P2 | 3/4" | sí (pared) |
| S2 | (0;0;2,5) – (1;0;2,5) | 1,000 | P1, P2 | 3/4" | no (techo, expuesto) |
| S3 | (1;0;2,5) – (1,5;0;2,5) | 0,500 | P1 | 1/2" | no |
| S4 | (1,5;0;0,6) – (1,5;0;2,5) | 1,900 | P1 | 1/2" | sí (pared) |
| S5 | (1;0;2,5) – (1;1,5;2,5) | 1,500 | P2 | 3/4" | no |
| S6 | (1;1,5;1,2) – (1;1,5;2,5) | 1,300 | P2 | 3/4" | sí (pared) |

Claves de segmento (formato `fuente|extremo menor|extremo mayor`, cada coordenada con tres decimales):

| Seg. | Clave |
|---|---|
| S1 | `F1\|0.000,0.000,0.000\|0.000,0.000,2.500` |
| S2 | `F1\|0.000,0.000,2.500\|1.000,0.000,2.500` |
| S3 | `F1\|1.000,0.000,2.500\|1.500,0.000,2.500` |
| S4 | `F1\|1.500,0.000,0.600\|1.500,0.000,2.500` |
| S5 | `F1\|1.000,0.000,2.500\|1.000,1.500,2.500` |
| S6 | `F1\|1.000,1.500,1.200\|1.000,1.500,2.500` |

Comprobación del orden: se compara (x, y, z) como tupla numérica; en S1, (0;0;0) < (0;0;2,5); en S4,
(1,5;0;0,6) < (1,5;0;2,5); en S6, (1;1,5;1,2) < (1;1,5;2,5).

**Longitud unida total** = 2,500 + 1,000 + 0,500 + 1,900 + 1,500 + 1,300 = **8,700 m**.

Contraste con la suma sin unir: 12,200 − 8,700 = **3,500 m** contados dos veces si no se uniera
(S1 = 2,500 más S2 = 1,000). Eso cubre **[FR-3]**: la tubería compartida no se cuenta dos veces.

Longitud unida por diámetro:

- 3/4": S1 + S2 + S5 + S6 = 2,500 + 1,000 + 1,500 + 1,300 = **6,300 m**
- 1/2": S3 + S4 = 0,500 + 1,900 = **2,400 m**
- Control: 6,300 + 2,400 = 8,700 m.

Longitud empotrada (picado y resane): S1 + S4 + S6 = 2,500 + 1,900 + 1,300 = **5,700 m**.

## 4. Conteo de codos y tees (spec §6.5)

Dibujo en alzado y planta esquemáticos. Los nodos son los vértices del árbol. La línea `|` es vertical
(pared); `---` es horizontal en el techo.

```
 ALZADO (vista desde -y; x hacia la derecha, z hacia arriba). Techo en z = 2,5.

   z=2,5   B ===S2=== E ---S3--- C
           ||         .          |
           ||         .          |
          S1         (S5 sale    S4  (baja 1,9)
           ||         hacia +y)  |
           ||                    |
   z=0,6   ||                    D  = punto P1 (lavamanos)
   z=0     A  = fuente F1
           x=0       x=1        x=1,5

 PLANTA (vista desde +z; y hacia arriba). Todo a z = 2,5 salvo las bajantes.

   y=1,5                  G  (baja S6 hasta H = punto P2, z = 1,2)
                          |
                          S5
                          |
   y=0     B ===S2=== E --S3-- C
           x=0        x=1      x=1,5

   Leyenda: === tramo compartido por P1 y P2; --- tramo de un solo punto.
   B, C, G: codos.  E: tee (concurren S2, S3, S5).
```

Nodos y segmentos que concurren:

| Nodo | Coordenadas | Segmentos concurrentes | d | Qué es |
|---|---|---|---|---|
| A | (0; 0; 0) | S1 | 1 | fuente (extremo) |
| B | (0; 0; 2,5) | S1, S2 | 2 | **codo** (vertical → horizontal) |
| E | (1; 0; 2,5) | S2, S3, S5 | 3 | **tee** (d − 2 = 1) |
| C | (1,5; 0; 2,5) | S3, S4 | 2 | **codo** (horizontal → vertical) |
| D | (1,5; 0; 0,6) | S4 | 1 | punto P1 (extremo) |
| G | (1; 1,5; 2,5) | S5, S6 | 2 | **codo** (horizontal → vertical) |
| H | (1; 1,5; 1,2) | S6 | 1 | punto P2 (extremo) |

- **Codos = 3** (nodos B, C, G). B está en un tramo compartido: cuenta **una vez** para el árbol, aunque
  lo recorren dos recorridos. Contar por recorrido daría B dos veces (una por P1 y otra por P2) y está mal.
- **Tees = 1** (nodo E, d = 3, d − 2 = 1). El giro del ramal de P2 hacia +y en E **no** se cuenta además
  como codo: la tee ya lo resuelve.
- Control con el recorrido del spec «sube, cruza en x, cruza en y, baja» (tres codos), aplicado a P2
  aislado: B, E, G = 3 codos. En el árbol unido E pasa a ser tee, así que P2 aporta B y G; el ramal de P1
  aporta C. Total del árbol: 3 codos y 1 tee.
- Diámetro de cada accesorio (supuesto declarado D-5): el mayor de los segmentos que concurren.
  Codo B: S1 y S2 → 3/4". Codo C: S3 y S4 → 1/2". Codo G: S5 y S6 → 3/4". Tee E: S2, S3, S5 → 3/4".
  Resumen: codos 3/4" = 2; codos 1/2" = 1; tees 3/4" = 1.

**Cajas** (spec §6.5: una por punto, más las declaradas en el recorrido): `P1` = 1, `P2` = 1, declaradas
= 0 → **2 cajas**. (La caja no es partida de la tabla de §7.1; se anota aquí para el oráculo de geometría.)

## 5. Partidas derivadas de agua (spec §7.1) con desperdicio

Constantes y su fuente. Ninguna tiene fuente verificada (ver `docs/bitacora/2026-10-sf.md`, tarea 0.4):
todas son **supuestos declarados** (RS-5) y deben verse en la hoja como tales.

| Id | Constante | Valor | Estado |
|---|---|---|---|
| D-1 | Desperdicio de tubería de agua fría | 10 % (factor 1,10) | **supuesto declarado**, sin fuente verificada |
| D-2 | Desperdicio de codos, tees, llaves, salidas y picado | 0 % (conteo exacto) | **supuesto declarado**; §7.1 solo prevé desperdicio para la tubería |
| D-3 | Altura del techo para el recorrido | alto del ambiente (2,5 m) | regla del spec §6.4, no constante externa |
| D-4 | Empotrado: tramos de pared empotrados; techo expuesto | por superficie | **supuesto declarado** del ejemplo (en sitio el usuario lo declara por segmento) |
| D-5 | Diámetro de un accesorio | mayor de los segmentos que concurren | **supuesto declarado**; el spec fija el diámetro del segmento compartido, no el del accesorio |

Cálculo paso a paso (todo en `Decimal`, sin redondeo intermedio):

1. Tubería 3/4": 6,300 m × (1 + 0,10) = 6,300 × 1,10 = **6,930 m**.
2. Tubería 1/2": 2,400 m × (1 + 0,10) = 2,400 × 1,10 = **2,640 m**.
3. Codos 3/4": **2 u**. Codos 1/2": **1 u**. Tees 3/4": **1 u**.
4. Llave de paso: una por punto de agua fría que la declare: `P1` sí, `P2` sí → **2 u**.
5. Picado y resane de pared (m): longitud unida empotrada = **5,700 m** (sin desperdicio, D-2).
6. Salida de agua (punto): una por punto → **2 u** (partida de §7.1; distinta de la caja de §6.5, que es conteo geométrico y también da 2).

Tabla final (la que compara el programa):

| Partida | Unidad | Longitud/conteo base | Desperdicio | Cantidad final |
|---|---|---|---|---|
| Tubería agua fría 3/4" | m | 6,300 | × 1,10 | 6,930 |
| Tubería agua fría 1/2" | m | 2,400 | × 1,10 | 2,640 |
| Codo 3/4" | u | 2 | ninguno | 2 |
| Codo 1/2" | u | 1 | ninguno | 1 |
| Tee 3/4" | u | 1 | ninguno | 1 |
| Llave de paso | u | 2 | ninguno | 2 |
| Picado y resane de pared | m | 5,700 | ninguno | 5,700 |
| Salida de agua | u | 2 | ninguno | 2 |

Las cantidades son exactas; el programa debe coincidir a ±0,001 (m) y exacto en conteos.

## 6. Casos degenerados documentados

### 6.1 Espacio vacío **[FR-1]**

Un proyecto sin ningún ambiente, fuente ni punto: `derivar(espacio, "agua")` devuelve `[]`. No es error.

### 6.2 Punto sin recorrido y fuente sin puntos **[FR-2]**

Se agrega al ejemplo, **aparte** (no cambia las cantidades de §5):

- Fuente `F2`: agua fría, en `BAN-01`, (2,000; 1,500; 0,000), **sin ningún punto**.
- Punto `P3`: llave de manguera, (1,800; 1,500; 0,400), declarado **sin fuente** (sin recorrido posible).

Resultado esperado:

| Elemento | Tramos | Longitud (m) | Codos | Tees | Observación |
|---|---|---|---|---|---|
| Árbol de `F2` | 0 | 0,000 | 0 | 0 | fuente sin puntos: no hay árbol ni segmentos |
| Recorrido de `P3` | 0 | 0,000 | 0 | 0 | sin recorrido: no se inventa uno |

No hay división por cero (ningún promedio ni cociente interviene en las reglas de §5) y **no** se emiten
tramos de largo cero. `F2` y `P3` **no entran** en la tabla final de §5: ese caso se prueba aparte y solo
exige que no haya tramos, ni longitud, ni codos, ni tees, ni excepción. Un recorrido cuyos vértices
consecutivos coinciden (largo cero) se trata igual: el tramo se omite, como el recorrido en y de P1 en §2.

## 7. Bloque machine-readable

La prueba `tests/unit/test_memoria_bano_of001.py` lee este bloque. Los valores decimales van como texto
para no pasar por `float`.

```json
{
  "unidades": "m",
  "tolerancia_m": "0.001",
  "desperdicio_tuberia": "0.10",
  "segmentos": [
    {"id": "S1", "clave": "F1|0.000,0.000,0.000|0.000,0.000,2.500", "longitud": "2.500", "diametro": "3/4", "empotrado": true, "sirve": ["P1", "P2"]},
    {"id": "S2", "clave": "F1|0.000,0.000,2.500|1.000,0.000,2.500", "longitud": "1.000", "diametro": "3/4", "empotrado": false, "sirve": ["P1", "P2"]},
    {"id": "S3", "clave": "F1|1.000,0.000,2.500|1.500,0.000,2.500", "longitud": "0.500", "diametro": "1/2", "empotrado": false, "sirve": ["P1"]},
    {"id": "S4", "clave": "F1|1.500,0.000,0.600|1.500,0.000,2.500", "longitud": "1.900", "diametro": "1/2", "empotrado": true, "sirve": ["P1"]},
    {"id": "S5", "clave": "F1|1.000,0.000,2.500|1.000,1.500,2.500", "longitud": "1.500", "diametro": "3/4", "empotrado": false, "sirve": ["P2"]},
    {"id": "S6", "clave": "F1|1.000,1.500,1.200|1.000,1.500,2.500", "longitud": "1.300", "diametro": "3/4", "empotrado": true, "sirve": ["P2"]}
  ],
  "recorridos": {
    "P1": {"longitud": "5.900", "tramos": ["2.500", "1.500", "1.900"]},
    "P2": {"longitud": "6.300", "tramos": ["2.500", "1.000", "1.500", "1.300"]}
  },
  "longitud_sin_unir": "12.200",
  "longitud_unida_total": "8.700",
  "longitud_unida_por_diametro": {"3/4": "6.300", "1/2": "2.400"},
  "longitud_empotrada": "5.700",
  "codos": {"3/4": 2, "1/2": 1},
  "tees": {"3/4": 1},
  "cajas": 2,
  "salidas_agua": 2,
  "puntos_con_llave": ["P1", "P2"],
  "partidas": [
    {"partida": "tuberia_3/4", "unidad": "m", "cantidad": "6.930"},
    {"partida": "tuberia_1/2", "unidad": "m", "cantidad": "2.640"},
    {"partida": "codo_3/4", "unidad": "u", "cantidad": "2"},
    {"partida": "codo_1/2", "unidad": "u", "cantidad": "1"},
    {"partida": "tee_3/4", "unidad": "u", "cantidad": "1"},
    {"partida": "llave_de_paso", "unidad": "u", "cantidad": "2"},
    {"partida": "picado_resane_pared", "unidad": "m", "cantidad": "5.700"},
    {"partida": "salida_agua", "unidad": "u", "cantidad": "2"}
  ],
  "degenerados": {
    "espacio_vacio": {"items": 0},
    "fuente_sin_puntos": {"tramos": 0, "longitud": "0.000", "codos": 0, "tees": 0},
    "punto_sin_recorrido": {"tramos": 0, "longitud": "0.000", "codos": 0, "tees": 0}
  }
}
```
