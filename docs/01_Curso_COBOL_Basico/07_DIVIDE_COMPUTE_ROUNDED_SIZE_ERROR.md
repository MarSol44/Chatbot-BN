---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-6.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 6 - DIVIDE, COMPUTE y opciones aritméticas"
temas: "DIVIDE INTO, DIVIDE BY GIVING, REMAINDER, ROUNDED, overflow, ON SIZE ERROR, NOT ON SIZE ERROR, END-ADD END-COMPUTE, tamaño de campos receptores, COMPUTE, orden de evaluación, números con signo S, funciones intrínsecas FUNCTION SQRT"
---

# Parte 6 – DIVIDE, COMPUTE, ROUNDED y ON SIZE ERROR
_Fuente: COBOL PARTE-6.ppt (27 diapositivas) · Expositor: Ing. Alfredo Asmat_

## DIVIDE … INTO (Formato 1)
```cobol
DIVIDE {identificador-1 | literal-1} INTO identificador-2 ...
```
Divide identificador-2 entre identificador-1; resultado en identificador-2.

Con X = 2, Y = 12, Z = 8:
| Instrucción | Resultado |
|---|---|
| `DIVIDE X INTO Y` | Y = 6 |
| `DIVIDE 3 INTO Y` | Y = 4 |
| `DIVIDE 2 INTO Y, Z` | Y = 6, Z = 4 |

## DIVIDE … GIVING (Formato 2)
```cobol
DIVIDE {identificador-1 | literal-1} {INTO | BY} {identificador-2 | literal-2}
       GIVING identificador-3 ...
```
Con X = 2, Y = 12, Z = 8:
| Instrucción | Resultado |
|---|---|
| `DIVIDE X INTO Y GIVING Z` | Z = 6 |
| `DIVIDE Y BY X GIVING Z` | Z = 6 |
| `DIVIDE 16 BY Z GIVING X, Y` | X = 2, Y = 2 |

## Cláusula REMAINDER
Guarda el residuo de la división. Con Q y R en PIC 99:
```cobol
DIVIDE 70 BY 15 GIVING Q REMAINDER R   *> Q = 4, R = 10
```

## Opción ROUNDED
- Por defecto, si el resultado tiene más decimales de los que caben, se **trunca**: 3.89 en PIC 9V9 → 3.8.
- Con **ROUNDED** se redondea según la PIC: 3.89 → 3.9.

```cobol
01 Amt1  PIC 9V99  VALUE 2.25.
01 Amt2  PIC 999.
```
| Instrucción | Resultado real | Valor almacenado |
|---|---|---|
| `MULTIPLY .3 BY Amt1` | .675 | Amt1 = 0.67 |
| `MULTIPLY .3 BY Amt1 ROUNDED` | .675 | Amt1 = 0.68 |
| `DIVIDE 150 BY 9 GIVING Amt2 ROUNDED` | 16.66… | Amt2 = 017 |

## Overflow (SIZE ERROR)
Ocurre cuando el resultado es demasiado grande para el campo receptor. Ej.: `ADD 350 TO 725 GIVING Num` = 1,075; si Num es PIC 999, se trunca el dígito de orden alto y se guarda **075**.

### ON SIZE ERROR / NOT ON SIZE ERROR
- `ON SIZE ERROR instrucción(es)`: se ejecutan si hay overflow.
- `NOT ON SIZE ERROR instrucción(es)`: se ejecutan si no hay overflow.
- Al usar cualquiera de las dos, cerrar con el terminador: **END-ADD, END-SUBTRACT, END-MULTIPLY, END-DIVIDE, END-COMPUTE**.
```cobol
ADD X TO Y GIVING Z
    ON SIZE ERROR     DISPLAY ' Resultado muy largo'
    NOT ON SIZE ERROR PERFORM Calc-Para
END-ADD
```

## Tamaño recomendado del campo receptor (números positivos)
- **Suma**: una posición más que el mayor de los sumandos.
- **Resta** (menor de mayor): tan grande como el minuendo.
- **Multiplicación**: suma de las longitudes de los operandos.
- **División**: suma del número de dígitos del dividendo y del divisor.

## COMPUTE
Instrucción aritmética general con símbolos en vez de verbos:
| Símbolo | Operación |
|---|---|
| `+` | ADD |
| `-` | SUBTRACT |
| `*` | MULTIPLY |
| `/` | DIVIDE |
| `**` | Exponenciación |

```cobol
COMPUTE identificador-1 ... = {expresión-aritmética | literal | identificador-2}
```
Con X = 9, Y = 4, Z = 12:
| Instrucción | Resultado |
|---|---|
| `COMPUTE Z = X * Y` | Z = 36 |
| `COMPUTE X = Z - Y + 2` | X = 10 |
| `COMPUTE X = Y` | X = 4 |
| `COMPUTE Z = Y ** 2` | Z = 16 |

### Orden de evaluación
1. `**` exponenciación primero.
2. `*` y `/` de izquierda a derecha.
3. `+` y `-` de izquierda a derecha.
4. `( )` anulan las reglas 1-3: lo que está entre paréntesis se evalúa primero.

Con X = 6, Y = 18, Z = 5:
| Instrucción | Resultado |
|---|---|
| `COMPUTE Z = Y / X + 3` | Z = 6 |
| `COMPUTE Z = Y / (X + 3)` | Z = 2 |
| `COMPUTE Y = Z + X * 10` | Y = 65 |
| `COMPUTE Y = Z * X / 10` | Y = 3 |

COMPUTE admite **ROUNDED** (tras el campo resultado) y ON SIZE ERROR / NOT ON SIZE ERROR (con END-COMPUTE).

## Números con signo
- Usar **S** en la PIC si los valores o el resultado pueden ser negativos.
- Una PIC sin S se asume sin signo: si el resultado es negativo, el campo **no retiene el signo**.

## Funciones intrínsecas
- Rutinas incorporadas para tareas como raíz cuadrada, convertir a mayúsculas, obtener la fecha actual.
- Aprobadas como extensiones del estándar COBOL en **1989**; incluidas en muchos compiladores.
- Categorías: calendario, análisis numérico, estadística, trigonometría, finanzas, caracteres y cadenas.
```cobol
COMPUTE Y = FUNCTION SQRT(X)   *> raíz cuadrada de X en Y
```
