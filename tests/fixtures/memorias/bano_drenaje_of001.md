# Memoria de cálculo a mano: drenaje del baño de OF-001

Oráculo del drenaje de la tarea 1.5 del sprint final (spec §6.4 drenaje, §6.5, §7.1). Complementa a
`bano_of001.md` (agua fría): mismo baño, mismas coordenadas de ambiente. Está hecha a mano, con
aritmética exacta (`Decimal`), y **no depende de ningún código del proyecto**. Las pruebas comparan contra
este archivo a ±0,001 m, no contra la expresión de ninguna regla.

**Naturaleza de los datos** (NORMAS.md §1). OF-001 es un caso construido para el proyecto. Las
coordenadas son **supuestos declarados** (números simples para contar a mano); no provienen de un plano.
Origen de medida de todas las filas: tipo *Supuesto*, motivo «ejemplo de memoria de cálculo».

**Sin pendiente numérica.** La longitud de un tramo es la distancia entre sus vértices en planta y en
alzado, con el piso en z = 0. La pendiente mínima del drenaje es la regla R10 de la tarea 1.6 (su fuente,
Gaceta Oficial N.º 4.044 Extraordinario de 1988, no está verificada: supuesto declarado RS-5) y **no
interviene aquí**: ninguna longitud de esta memoria se altera por pendiente.

Unidades: metros. Eje z hacia arriba desde el piso terminado. Tolerancia geométrica: 0,001 m.

## 1. Modelo espacial de ejemplo

Se agregan al baño de `bano_of001.md` (ambiente `BAN-01`: 2,000 × 1,500 × 2,500) una fuente y dos puntos:

| Tabla | Fila | Datos |
|---|---|---|
| Fuente | `FD1` | colector de drenaje, ambiente `BAN-01`, (x, y, z) = (2,000; 0,750; 0,000) |
| Punto | `D1` | desagüe de la ducha, drenaje, **piso**, (1,000; 1,500; 0,000), fuente `FD1`, diámetro 2" |
| Punto | `D2` | desagüe del lavamanos, drenaje, **pared**, (1,500; 0,000; 0,500), fuente `FD1`, diámetro 1 1/2" |

Ni `D1` ni `D2` declaran llave de paso (el drenaje no lleva llave: spec §7.1 la pide solo para agua fría).

## 2. Recorrido propuesto de cada punto (spec §6.4, drenaje)

Regla: desde el punto **baja al piso**, recorre en x y luego en y **por el piso**, hasta el colector. Un
tramo de largo cero **se omite**.

**Recorrido de `D1`** (vértices): A(1; 1,5; 0) → B(2; 1,5; 0) → C(2; 0,75; 0)

| Tramo | De → a | Superficie | Cálculo | Longitud (m) |
|---|---|---|---|---|
| (baja) | A → A | pared | 0 − 0, omitido (el punto ya está en el piso) | 0 |
| D1-1 | A → B (en x) | piso | 2 − 1 | 1,000 |
| D1-2 | B → C (en y) | piso | 1,5 − 0,75 | 0,750 |

Longitud del recorrido de `D1`: 1,0 + 0,75 = **1,750 m**.

**Recorrido de `D2`** (vértices): E(1,5; 0; 0,5) → F(1,5; 0; 0) → G(2; 0; 0) → C(2; 0,75; 0)

| Tramo | De → a | Superficie | Cálculo | Longitud (m) |
|---|---|---|---|---|
| D2-1 | E → F (baja) | pared | 0,5 − 0 | 0,500 |
| D2-2 | F → G (en x) | piso | 2 − 1,5 | 0,500 |
| D2-3 | G → C (en y) | piso | 0,75 − 0 | 0,750 |

Longitud del recorrido de `D2`: 0,5 + 0,5 + 0,75 = **1,750 m**.

Suma sin unir: 1,75 + 1,75 = 3,500 m. Los dos recorridos no comparten ningún tramo (llegan al colector por
lados opuestos, sobre la misma recta x = 2), así que la longitud unida es también 3,500 m.

## 3. Segmentos únicos

Clave = `fuente|extremo menor|extremo mayor` (cada coordenada con tres decimales; se compara (x, y, z)).

| Seg. | Extremos | Longitud (m) | Sirve a | Diámetro | Superficie | Empotrado |
|---|---|---|---|---|---|---|
| SD1 | (1;1,5;0) – (2;1,5;0) | 1,000 | D1 | 2" | piso | sí |
| SD2 | (2;0,75;0) – (2;1,5;0) | 0,750 | D1 | 2" | piso | sí |
| SD3 | (1,5;0;0) – (1,5;0;0,5) | 0,500 | D2 | 1 1/2" | pared | sí |
| SD4 | (1,5;0;0) – (2;0;0) | 0,500 | D2 | 1 1/2" | piso | sí |
| SD5 | (2;0;0) – (2;0,75;0) | 0,750 | D2 | 1 1/2" | piso | sí |

| Seg. | Clave |
|---|---|
| SD1 | `FD1\|1.000,1.500,0.000\|2.000,1.500,0.000` |
| SD2 | `FD1\|2.000,0.750,0.000\|2.000,1.500,0.000` |
| SD3 | `FD1\|1.500,0.000,0.000\|1.500,0.000,0.500` |
| SD4 | `FD1\|1.500,0.000,0.000\|2.000,0.000,0.000` |
| SD5 | `FD1\|2.000,0.000,0.000\|2.000,0.750,0.000` |

**Empotrado por defecto (decisión D-4 corregida).** Un tramo de pared o de piso es empotrado; techo,
plafón y bandeja son expuestos. Un drenaje corre enterrado en la losa o el contrapiso: sin esta regla no
habría picado de piso por defecto y la partida «picado y resane de pared o piso» de spec §7.1 solo
existiría por sobrescritura.

**Longitud unida total** = 1,000 + 0,750 + 0,500 + 0,500 + 0,750 = **3,500 m**.

Por diámetro:

- 2": SD1 + SD2 = 1,000 + 0,750 = **1,750 m**
- 1 1/2": SD3 + SD4 + SD5 = 0,500 + 0,500 + 0,750 = **1,750 m**
- Control: 1,750 + 1,750 = 3,500 m.

Empotrado por superficie: piso = SD1 + SD2 + SD4 + SD5 = 1,000 + 0,750 + 0,500 + 0,750 = **3,000 m**;
pared = SD3 = **0,500 m**; total empotrado = 3,500 m.

## 4. Conteo de codos y tees (spec §6.5)

```
 PLANTA (vista desde +z; y hacia arriba; todo a z = 0 salvo la bajante de D2).

   y=1,5   D1 ====SD1==== B
                          |
                         SD2
                          |
   y=0,75                 C  = colector FD1 (recorre en línea recta: SD2 y SD5 son colineales)
                          |
                         SD5
                          |
   y=0     E(baja SD3) -SD4- G
           x=1,5          x=2
   (D1 en x = 1; E es el desagüe de D2 en x = 1,5, a z = 0,5 sobre el piso en F)
```

| Nodo | Coordenadas | Segmentos concurrentes | d | Qué es |
|---|---|---|---|---|
| A (= D1) | (1; 1,5; 0) | SD1 | 1 | punto D1 (extremo) |
| B | (2; 1,5; 0) | SD1, SD2 | 2 | **codo** (x → y) |
| C (= FD1) | (2; 0,75; 0) | SD2, SD5 | 2 | colineales: ni codo ni tee |
| F | (1,5; 0; 0) | SD3, SD4 | 2 | **codo** (vertical → horizontal) |
| G | (2; 0; 0) | SD4, SD5 | 2 | **codo** (x → y) |
| E (= D2) | (1,5; 0; 0,5) | SD3 | 1 | punto D2 (extremo) |

- Codos = 3: B (diámetro 2"), F y G (diámetro 1 1/2"). Tees = 0.
- Diámetro de un accesorio (D-5): el mayor de los segmentos que concurren. B: SD1 y SD2, 2". F: SD3 y SD4,
  1 1/2". G: SD4 y SD5, 1 1/2".
- En C concurren SD2 (2") y SD5 (1 1/2") sobre la misma recta: no hay accesorio de cambio de dirección. El
  cambio de diámetro (reducción) **no** es parte de §6.5 y no se cuenta.
- Resumen: codos 2" = 1; codos 1 1/2" = 2; tees = 0.

## 5. Partidas derivadas de drenaje (spec §7.1) con desperdicio

Constantes (ninguna con fuente verificada: son **supuestos declarados**, RS-5):

| Id | Constante | Valor | Estado |
|---|---|---|---|
| D-1b | Desperdicio de tubería de drenaje | 10 % (factor 1,10) | **supuesto declarado**, sin fuente verificada |
| D-2 | Desperdicio de codos, tees, salidas y picado | 0 % (conteo exacto) | **supuesto declarado** |
| D-4 | Empotrado por defecto: pared y piso | por superficie | **supuesto declarado** (corregida: antes solo pared) |
| D-5 | Diámetro de un accesorio | mayor de los segmentos que concurren | **supuesto declarado** |
| D-6 | Material por defecto de la tubería | PVC | **supuesto declarado** (el punto puede declarar otro) |

Cálculo (`Decimal`, sin redondeo intermedio):

1. Tubería de drenaje 2": 1,750 × 1,10 = **1,925 m**.
2. Tubería de drenaje 1 1/2": 1,750 × 1,10 = **1,925 m**.
3. Codos de drenaje 2": **1 u**. Codos de drenaje 1 1/2": **2 u**. Tees: ninguna.
4. Llave de paso: **no aplica** al drenaje.
5. Picado y resane de piso: **3,000 m**. Picado y resane de pared: **0,500 m** (sin desperdicio, D-2).
6. Salida de drenaje (punto): una por punto → **2 u**.

| Partida | Unidad | Base | Desperdicio | Cantidad final |
|---|---|---|---|---|
| Tubería de drenaje 2" | m | 1,750 | × 1,10 | 1,925 |
| Tubería de drenaje 1 1/2" | m | 1,750 | × 1,10 | 1,925 |
| Codo de drenaje 2" | u | 1 | ninguno | 1 |
| Codo de drenaje 1 1/2" | u | 2 | ninguno | 2 |
| Picado y resane de piso (drenaje) | m | 3,000 | ninguno | 3,000 |
| Picado y resane de pared (drenaje) | m | 0,500 | ninguno | 0,500 |
| Salida de drenaje | u | 2 | ninguno | 2 |

## 6. Bloque machine-readable

La prueba `tests/unit/test_memoria_bano_drenaje_of001.py` lee este bloque. Los decimales van como texto.

```json
{
  "unidades": "m",
  "tolerancia_m": "0.001",
  "desperdicio_tuberia": "0.10",
  "segmentos": [
    {"id": "SD1", "clave": "FD1|1.000,1.500,0.000|2.000,1.500,0.000", "longitud": "1.000", "diametro": "2", "superficie": "piso", "empotrado": true, "sirve": ["D1"]},
    {"id": "SD2", "clave": "FD1|2.000,0.750,0.000|2.000,1.500,0.000", "longitud": "0.750", "diametro": "2", "superficie": "piso", "empotrado": true, "sirve": ["D1"]},
    {"id": "SD3", "clave": "FD1|1.500,0.000,0.000|1.500,0.000,0.500", "longitud": "0.500", "diametro": "1 1/2", "superficie": "pared", "empotrado": true, "sirve": ["D2"]},
    {"id": "SD4", "clave": "FD1|1.500,0.000,0.000|2.000,0.000,0.000", "longitud": "0.500", "diametro": "1 1/2", "superficie": "piso", "empotrado": true, "sirve": ["D2"]},
    {"id": "SD5", "clave": "FD1|2.000,0.000,0.000|2.000,0.750,0.000", "longitud": "0.750", "diametro": "1 1/2", "superficie": "piso", "empotrado": true, "sirve": ["D2"]}
  ],
  "recorridos": {
    "D1": {"longitud": "1.750", "tramos": ["1.000", "0.750"]},
    "D2": {"longitud": "1.750", "tramos": ["0.500", "0.500", "0.750"]}
  },
  "longitud_sin_unir": "3.500",
  "longitud_unida_total": "3.500",
  "longitud_unida_por_diametro": {"2": "1.750", "1 1/2": "1.750"},
  "longitud_empotrada": {"piso": "3.000", "pared": "0.500"},
  "codos": {"2": 1, "1 1/2": 2},
  "tees": {},
  "salidas_drenaje": 2,
  "partidas": [
    {"partida": "tuberia_2", "unidad": "m", "cantidad": "1.925"},
    {"partida": "tuberia_1 1/2", "unidad": "m", "cantidad": "1.925"},
    {"partida": "codo_2", "unidad": "u", "cantidad": "1"},
    {"partida": "codo_1 1/2", "unidad": "u", "cantidad": "2"},
    {"partida": "picado_resane_piso", "unidad": "m", "cantidad": "3.000"},
    {"partida": "picado_resane_pared", "unidad": "m", "cantidad": "0.500"},
    {"partida": "salida_drenaje", "unidad": "u", "cantidad": "2"}
  ]
}
```
