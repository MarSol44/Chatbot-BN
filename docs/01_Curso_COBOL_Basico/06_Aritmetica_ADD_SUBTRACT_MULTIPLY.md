---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-5.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 5 - Instrucciones ADD, SUBTRACT, MULTIPLY"
temas: "aritmética básica, ADD TO, ADD GIVING, SUBTRACT FROM, SUBTRACT GIVING, MULTIPLY BY, MULTIPLY GIVING, ejemplos con resultados"
---

# Parte 5 – Aritmética: ADD, SUBTRACT, MULTIPLY
_Fuente: COBOL PARTE-5.ppt (20 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Reglas generales
ADD, SUBTRACT, MULTIPLY y DIVIDE requieren que los campos operados:
- tengan cláusula PICTURE **numérica**, y
- contengan datos **numéricos** al ejecutarse la instrucción.

## ADD … TO (Formato 1)
```cobol
ADD {identificador-1 | literal-1} ... TO identificador-2 ...
```
- Se suma identificador-1/literal-1 a identificador-2; el resultado queda en **identificador-2** (su valor original se reemplaza).
- Los identificadores **antes** de TO no cambian.

Con X = 5, Y = 3, Z = 7:
| Instrucción | Resultado |
|---|---|
| `ADD X TO Y` | Y = 8 |
| `ADD X, 9 TO Y` | Y = 17 |
| `ADD X, 6, Y TO Z` | Z = 21 |
| `ADD X, Y TO Z` | Z = 15 |

## ADD … GIVING (Formato 2)
```cobol
ADD {identificador-1 | literal-1} ... GIVING identificador-2 ...
```
- Se suman todos los términos antes de GIVING; el resultado se guarda en el campo después de GIVING (su valor original **no** participa en la suma, se reemplaza).
- Los identificadores antes de GIVING no cambian.
- El campo receptor puede ser un **campo de reporte con símbolos de edición**.

Con X = 5, Y = 3, Z = 7:
| Instrucción | Resultado |
|---|---|
| `ADD X, Y GIVING Z` | Z = 8 |
| `ADD X, 10 GIVING Y` | Y = 15 |
| `ADD X, 4, Y GIVING Z` | Z = 12 |
| `ADD X, 6 GIVING Y, Z` | Y = 11, Z = 11 |

## SUBTRACT … FROM
```cobol
SUBTRACT {identificador-1 | literal-1} ... FROM identificador-2 ...
```
- Resta identificador-1/literal-1 de identificador-2; resultado en identificador-2.
- Reglas: todo debe ser numérico; después de FROM debe ir un **nombre de dato, no un literal**; el resultado se guarda en el campo después de FROM.

Con A = 6, B = 2, C = 18:
| Instrucción | Resultado |
|---|---|
| `SUBTRACT A FROM C` | C = 12 |
| `SUBTRACT B, 5 FROM C` | C = 11 |
| `SUBTRACT B FROM A, C` | A = 4, C = 16 |

## SUBTRACT … GIVING
```cobol
SUBTRACT {identificador-1 | literal-1} ... FROM {identificador-2 | literal-2}
         GIVING identificador-3 ...
```
- Resultado en identificador-3. Todo lo que va antes de GIVING debe ser numérico; GIVING debe ir seguido de un nombre de dato (numérico o campo de reporte editado).

Con A = 6, B = 2, C = 18:
| Instrucción | Resultado |
|---|---|
| `SUBTRACT B FROM A GIVING C` | C = 4 |
| `SUBTRACT A FROM 15 GIVING C` | C = 9 |
| `SUBTRACT A, 4 FROM C GIVING B` | B = 8 |

## MULTIPLY … BY
```cobol
MULTIPLY {identificador-1 | literal-1} BY identificador-2 ...
```
Resultado en identificador-2.

Con Q = 4, R = 7, S = 5:
| Instrucción | Resultado |
|---|---|
| `MULTIPLY Q BY R` | R = 28 |
| `MULTIPLY 10 BY S` | S = 50 |
| `MULTIPLY 2 BY R, S` | R = 14, S = 10 |

## MULTIPLY … GIVING
Con Q = 4, R = 7, S = 5:
| Instrucción | Resultado |
|---|---|
| `MULTIPLY Q BY R GIVING S` | S = 28 |
| `MULTIPLY Q BY 3 GIVING S` | S = 12 |
| `MULTIPLY 6 BY Q GIVING R, S` | R = 24, S = 24 |

Ver DIVIDE, COMPUTE, ROUNDED y ON SIZE ERROR en el archivo `07_DIVIDE_COMPUTE_ROUNDED_SIZE_ERROR.md`.
