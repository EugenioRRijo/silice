# Memoria de cálculo del comparador y de las métricas del experimento (S4 §9.5, §10.1)

Escrita **a mano antes del código** (oráculo independiente: no sale de ninguna salida de un modelo
ni de
la derivación que se prueba). Las pruebas `tests/unit/test_experimento_comparador.py` y
`tests/unit/test_experimento_metricas.py` verifican estas cifras. Datos construidos y declarados
(NORMAS §1).

## 1. La referencia del comparador

Un baño, metros, esquina en el origen: ambiente A de 2,4 × 1,5 × 2,5; fuente F (montante de agua) en
(0; 0; 0); punto P1 (agua fría, pared) en (1,5; 0; 0,6) y punto P2 (agua fría, pared) en (1,0; 1,5;
1,2),
los dos alimentados por F.

## 2. Emparejamiento y clasificación (regla cerrada)

Tolerancia de emparejamiento 0,10 m; tolerancia de medida 0,001 m.

- **Mismos elementos con otros ids y en otro orden**: sin errores; P1 ↔ el punto en (1,5; 0; 0,6)
- **P1 con x = 1,55 (a 0,05 m)**: un par; x difiere en 0,05 > 0,001 → **E3** (campo x)
- **P1 con x = 1,60 (a 0,10 m exactos)**: todavía empareja → **E3**
- **P1 con x = 1,61 (a 0,11 m)**: no empareja: P1 sin par → **E6**; el punto del borrador sin par →
  **E7**
- **P1 con x = 1,501 (a 0,001 m)**: empareja y la diferencia no excede 0,001 → sin error; con 1,502
  → **E3**
- **Dos puntos de la referencia en x = 1,0 y x = 1,1 y un punto del borrador en x = 1,05**: empate
  de distancias (0,05 y 0,05): gana la menor coordenada de la referencia (x = 1,0) → E3 en x y
  **E6** del otro; con la referencia en otro orden, lo mismo
- **Un segundo punto del borrador a menos de 0,001 m de uno ya emparejado**: **E7** (duplicado)
- **Punto con otro `ambiente_id` (hay dos ambientes)**: **E4**
- **Punto con otra fuente**: **E5**
- **Punto a 0,05 m del muro, fuera de todo ambiente**: **E3** (x) y **E4** (fuera)
- **Borrador trasladado (+10; +20) y tarea de posición libre**: sin errores y traslación (−10; −20)
  registrada
- **Partidas: mismo código y unidad; código distinto con unidad compatible; unidad incompatible**:
  sin error; **E1**; **E2**
- **Partida de más / de menos**: **E7** / **E6**; cantidad distinta → **E3** (campo cantidad)
- **E8: sembrado «P1.x = 3,00», borrador con x = 3,00**: **E8** (no E3, ni E4 «fuera»); con x = 1,5:
  nada; con x = 2,0: E6 + E7; sin el punto: E6


## 3. Hallazgos esperados por construcción, detección y falsa alarma

Referencia con dos hallazgos R8 de ADVERTENCIA sobre el ambiente. Borrador con ids renombrados y un
error
E3 en el punto q1. Hallazgos del borrador: tres R8 sobre el ambiente (dos esperados + uno **no**
esperado),
un R9 sobre `esp_puntos:q1` y un R10 sobre `esp_puntos:q2` (fila limpia). Resultado: el error E3
queda
**detectado** (el R9 cita su fila); no esperados = 3 (el tercer R8, R9 y R10); **falsas alarmas =
2**
(el tercer R8 y el R10 no citan ninguna fila con error). Un error sin fila (E6) o sin hallazgo
**escapa**.

## 4. Métricas

Modelo M, condición A, tres corridas:
- T1 rep. 1: errores E3(q1) y E6; detecta E3; 2 hallazgos no esperados, 1 falsa alarma.
- T1 rep. 2: error E3(q1); nada lo detecta; 0 no esperados.
- T2 rep. 1: errores E4 y E3; detecta los dos; 3 no esperados, 0 falsas.

Detectables por hipótesis: E3 y E4 (E6 no lo es). Detectables = 1 + 1 + 2 = **4**; detectados = 1 +
0 + 2 =
**3** → **75 %**. Por tipo: E3 2/3, E4 1/1. Escapan: E3 = 1; no detectables por diseño: E6 = 1.
Falsas
alarmas = 1 de 5 no esperados = **20 %**. Propuestas válidas = 9 de 10. Exhaustividad = 11 de 12.
Por
tarea: T1 (1, 2), T2 (2, 2).

## 5. Bootstrap agrupado y Wilson

Bootstrap con las dos tareas (1/2 y 2/2): las razones posibles son 1/2 (T1, T1), 3/4 (T1, T2 o T2,
T1) y 1
(T2, T2) con probabilidades 1/4, 1/2 y 1/4 → percentil 2,5 = **0,5** y percentil 97,5 = **1,0** con
cualquier semilla. Una sola tarea da un intervalo degenerado (la razón de esa tarea).

Wilson al 95 % (z = 1,959964): 24/24 → [24/(24 + z²), 1] = **[0,8620; 1]**; 0/24 → **[0; 0,1380]**;
12/24 → **[0,3143; 0,6857]**.

## 6. Costos de la prueba

Tarifa de Opus 5.5 (4,00, 20,00 y 0,20 USD por millón de fichas): 10 000 de entrada + 3 000 de
salida +
6 000 de caché = 0,04 + 0,06 + 0,0012 = **0,1012 USD** por turno; 12 turnos = **1,2144 USD**, la
cota de
≈ 1,21 USD por tarea de S4 §8.4 (sin la escritura inicial de la caché).
