# Pruebas intermitentes del front: `Retomar` y `AutocompletadoDeInsumos` (2026-11-12)

Rama `fix/pruebas-intermitentes` (árbol `.worktrees/flaky`, nace de `feature/lector-topes`). `docs/ESTADO.md` (sección 3) las
listaba como «intermitentes con la máquina cargada (pasan solas)». Las dos eran defectos **de la prueba**, no del producto;
ninguna se arregló subiendo plazos ni reintentando.

## 1. Cómo se reprodujo (antes de tocar nada)

Carga: la suite completa corriendo a la vez (`npx vitest run --maxWorkers=8`) y, en paralelo, cada archivo repetido 30 veces.

```
cd frontend-desktop
npx vitest run --maxWorkers=8                                                          # la carga
npx vitest run src/paginas/hoja/Retomar.test.tsx --repeats 30
npx vitest run src/paginas/componer/AutocompletadoDeInsumos.test.tsx --repeats 30
```

| Prueba | Antes (30 repeticiones del archivo, con carga) | Error literal |
|---|---|---|
| `Retomar: lee el borrador vivo, muestra sus cambios…` | 4 fallos de 30 | `AssertionError: expected false to be true` en `Retomar.test.tsx:249` (`expect(saleLaPagina()).toBe(true)`) |
| `lo escrito y no elegido también queda marcado como propio…` | 12 fallos de 30 (y 1 en la pasada de la suite completa) | `Unable to find role="option" and name /Cemento gris ficticio/` en `AutocompletadoDeInsumos.test.tsx:280` |

## 2. Causa raíz

**`Retomar.test.tsx:249`.** El aviso de `beforeunload` se registra en un `useEffect` (efecto pasivo) de
`ProveedorDeLaHoja.tsx` (`window.addEventListener("beforeunload", …)`, dependiente de `hayCambios`). `findByRole("region",
{ name: "Estado del borrador" })` resuelve en cuanto el DOM ya muestra el estado; React vacía los efectos pasivos en un turno
posterior al commit. Con la máquina descargada ese turno llega antes de la siguiente línea; cargada, no, y `saleLaPagina()` miraba
una ventana sin oyente. Es una carrera entre la prueba y el planificador de React, no un plazo del producto.

**`AutocompletadoDeInsumos.test.tsx:280`.** La prueba escribe «Cemento gris», pulsa Tab y hace clic otra vez en la descripción.
`CampoConBusqueda` busca tras una pausa **real** de 300 ms (`PAUSA_MS`) y solo abre la lista si la respuesta llega con el campo
enfocado (`setAbierta(enfocado.current)`); un clic en el campo no abre nada por sí solo. Con la máquina descargada, el Tab y el clic
caben en menos de 300 ms, la respuesta llega con foco y la lista se abre: la prueba pasaba por esa coincidencia de tiempos. Con
carga, la pausa vence entre el Tab y el clic, la respuesta llega sin foco, la lista queda cerrada y `findByRole("option")` agota su
segundo. Se comprobó de forma determinista (sin carga): esperar a que la búsqueda haya salido antes del clic hace fallar la prueba
siempre (rojo visto).

## 3. Qué cambió

- `Retomar.test.tsx`: la comprobación del aviso espera la condición (`await esperar(() => expect(saleLaPagina()).toBe(true))`),
  con el auxiliar de la propia prueba, que da turnos a React dentro de `act`. Sin plazo nuevo.
- `AutocompletadoDeInsumos.test.tsx`: la prueba fija el orden que antes dependía del reloj (espera a que la búsqueda haya
  salido con el campo sin foco) y reabre la lista con `{ArrowDown}`, que funciona en cualquier orden: con la respuesta ya
  hecha abre la lista; con la búsqueda aún pendiente o en vuelo, la repite. Lo que la prueba verifica (el aviso de descripción
  propia desaparece al elegir del catálogo) queda igual. El producto no cambia.

## 4. Después

Mismo comando, mismas 30 repeticiones por archivo y la misma carga (suite completa con `--maxWorkers=8` a la vez):

| Archivo | Antes | Después |
|---|---|---|
| `Retomar.test.tsx` (32 pruebas × 30) | 4 fallos | 0 fallos (`Tests 32 passed (32)`) |
| `AutocompletadoDeInsumos.test.tsx` (20 pruebas × 30) | 12 fallos | 0 fallos (`Tests 20 passed (20)`) |

En la pasada de la suite completa bajo esa misma carga ya no falló ninguna de las dos; falló una ajena, `Costos del período >
anular pide el motivo y no borra la fila hasta recargar` (`CostosDelPeriodo.test.tsx`), la intermitente que la bitácora del
2026-11-01 ya registra. No se tocó: no estaba en el encargo.

## 5. Otras instancias del mismo patrón (no tocadas)

`Edicion.test.tsx:590` hace `findByText(/· 2 cambios sin guardar/)` y enseguida `expect(saleLaPagina()).toBe(true)`: la misma
carrera con el efecto de `beforeunload`. No falló en la reproducción, pero conviene darle el mismo arreglo.
