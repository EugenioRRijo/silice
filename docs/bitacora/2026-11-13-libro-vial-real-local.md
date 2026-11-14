# Prueba local del libro vial real con el perfil de un APU por hoja (2026-11-13)

Lo pedía `docs/ESTADO.md` §5.4: probar una vez, en local, el libro vial real con el perfil `apu_por_hoja`. La prueba la
hizo un subagente de Claude en el equipo de Eugenio, por el camino del producto (`POST /v1/libros/apu-por-hoja` con
`TestClient`), con perfiles locales escritos solo en la carpeta de trabajo del agente. **Ningún dato del libro está en
este repositorio**: ni nombres, ni códigos, ni cifras, ni recuentos (NORMAS §1). El informe con las mediciones vive solo
en el Escritorio de Eugenio («Prueba libro vial real (solo local) 2026-11-13.md»). Gemini no vio el libro.

## 1. Resultado

- El libro y su presupuesto **pasan los topes** del lector, en menos de dos segundos por libro y con pocos MB de memoria.
- Con el perfil del paquete, el libro no se reconoce (422): sus hojas no empiezan por el prefijo del perfil ficticio. Es
  lo esperado: el perfil de un libro real vive en la instalación (`docs/manual_tecnico.md` §18).
- Con un perfil local, todas las peticiones responden 200, sin ningún 500, y se reconocen todos los APU. Dos defectos
  del programa daban hallazgos falsos; los dos están corregidos (§2) y una segunda medición con la corrección lo
  confirma: ya no hay AH1 ERROR falsos ni AH6 por ruido, y los AH5 frente al presupuesto original son verdaderos.

## 2. Defectos y su corrección (rama `fix/lector-apu-por-hoja`, TDD con casos ficticios)

| # | Defecto | Corrección | Commits |
|---|---|---|---|
| 1 | El libro escribe cada porcentaje del pie a la **izquierda** de su rótulo y el monto a la derecha; el lector tomaba «el primer número a la derecha», es decir el monto, y daba AH1 ERROR falso en cada hoja | El perfil declara `lado_de_los_porcentajes` («derecha» por omisión, como hasta hoy; «izquierda» toma el número más cercano a la izquierda). Un valor distinto rechaza el perfil | `b8c992e4` (rojo), `5d2d2683` (verde) |
| 2 | La cantidad del presupuesto es el valor en caché de una fórmula y llega como doble con ruido binario (0,1 + 0,2 = 0.30000000000000004): AH6 falsos y un mensaje con la cifra ruidosa | `numero_de` toma cada `float` con 15 dígitos significativos, la precisión que Excel garantiza. Un `Decimal` o un entero no cambian | `b8c992e4` (rojo), `5d2d2683` (verde) |

**Por qué declarar el lado y no adivinarlo.** Adivinar (el número que «parece» porcentaje) confundiría el monto con el
porcentaje sin avisar en cuanto los dos sean parecidos; el perfil ya es quien dice dónde está cada cosa (por rótulos), y
el valor por omisión deja igual todo libro que hoy se lee bien. **Por qué 15 dígitos.** Es la precisión documentada de
Excel; más allá de ella el doble solo trae ruido. La prueba escribe el valor en el XML de la celda con 17 dígitos, como
Excel, porque openpyxl lo redondea a 16 al guardar y borraría el ruido.

## 3. Límites que no son defectos hoy (trabajo siguiente)

1. El perfil admite una sola hoja de presupuesto (`presupuesto.hoja`); un libro con un presupuesto por frente necesita un
   perfil por frente.
2. Una segunda fila de impuesto («otros impuestos») no se suma.
3. El rótulo del precio unitario del perfil del paquete coincide primero con la fila «sin impuesto»; con impuesto 0 da lo
   mismo.
4. Una hoja que no empieza por el prefijo del perfil se salta sin un hallazgo que lo diga.
5. No hay perfil local instalado ni forma de ponerlo desde la interfaz: hoy se copia a mano en
   `<carpeta de datos>/perfiles_libros/`.
