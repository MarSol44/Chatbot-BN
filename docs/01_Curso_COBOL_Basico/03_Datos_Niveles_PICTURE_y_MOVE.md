---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-2.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 2 - COBOL Básico: registros, números de nivel, PIC, MOVE"
temas: "group items, registros, números de nivel 01-49 66 77 88, PIC X A 9, MOVE alfanumérico, MOVE numérico, truncamiento, literales, constantes figurativas ZEROS SPACES"
---

# Parte 2 – Registros, números de nivel, PICTURE y MOVE
_Fuente: COBOL PARTE-2.ppt (30 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Registros y elementos de grupo
Un mismo dato de 26 caracteres (`HENNESSY RM 9230165 LM51 0550 F`) puede definirse de forma plana o como grupo:

```cobol
WORKING-STORAGE SECTION.
01  StudentDetails        PIC X(26).
```
```cobol
WORKING-STORAGE SECTION.
01  StudentDetails.
    02  StudentName.
        03  Surname       PIC X(8).
        03  Initials      PIC XX.
    02  StudentId         PIC 9(7).
    02  CourseCode        PIC X(4).
    02  Grant             PIC 9(4).
    02  Gender            PIC X.
```

## Números de nivel (jerarquía de datos)
- Descomponen una estructura en sus partes. **Cuanto más alto el número, más bajo está el elemento en la jerarquía.** En el nivel más bajo el dato es atómico.
- **01 a 49**: números de nivel generales. **66, 77 y 88**: niveles especiales.
- Lo importante es la **relación** entre números de nivel, no los valores concretos: usar 01/02/03 equivale a usar 01/05/10.

## Elementos de grupo
- "Elemento de grupo" = dato que ha sido subdividido. Se declara con nivel y nombre, **sin cláusula PIC**.
- Si es el más alto de la jerarquía se le llama **registro** y usa el nivel **01**.
- Su tamaño es la suma de sus subordinados y su tipo se asume siempre **PIC X** (porque puede contener subordinados de distintos tipos).

## Tipos de datos básicos
| PIC | Tipo |
|---|---|
| `X` | Alfanumérico |
| `A` | Alfabético |
| `9` | Numérico |

Esta simplicidad se paga con una instrucción de asignación compleja: **MOVE**.

## El verbo MOVE
- Copia datos de un identificador o literal origen a **uno o más** identificadores destino.
- Origen y destino pueden ser grupos o elementos elementales.
- Al mover a un campo, su contenido se **reemplaza completamente**.

### MOVE a campo alfanumérico/alfabético (PIC X o A)
Se copia **de izquierda a derecha**, rellenando con espacios o truncando **por la derecha**.
```cobol
01 Surname  PIC X(8).
MOVE "RYAN"        TO Surname.   *> "RYAN    "
MOVE "FITZPATRICK" TO Surname.   *> "FITZPATR"  (se trunca por la derecha)
```

### MOVE a campo numérico
- Los datos se **alinean por el punto decimal**, rellenando con ceros o truncando según sea necesario.
- Si no hay punto decimal explícito, se asume inmediatamente después del dígito más a la derecha.
- Parte entera: se mueve de derecha a izquierda; posiciones de orden alto no llenadas → ceros; si no cabe → **se truncan los dígitos de orden alto**.
- Parte decimal: se mueve de izquierda a derecha desde el punto; posiciones de orden bajo no llenadas → ceros.

```cobol
01 GrossPay   PIC 9(4)V99.
MOVE ZEROS     TO GrossPay.   *> 0000^00
MOVE 12.4      TO GrossPay.   *> 0012^40
MOVE 123.456   TO GrossPay.   *> 0123^45  (se pierde el 6)
MOVE 12345.757 TO GrossPay.   *> 2345^75  (se pierden el 1 y el 7 final)

01 CountyPop  PIC 999.
MOVE 1234 TO CountyPop.       *> 234
MOVE 12.4 TO CountyPop.       *> 012

01 Price      PIC 999V99.
MOVE 154     TO Price.        *> 154^00
MOVE 3552.75 TO Price.        *> 552^75
```
(`^` = punto decimal implícito `V`.)

- Hay combinaciones de tipos origen/destino que **no son válidas** en COBOL (tabla de "movimientos legales" presentada como imagen en la diapositiva 17).

## Formatos de MOVE
- **Formato 1**: `MOVE identificador-1 TO identificador-2` — ambos definidos en la DATA DIVISION. Para que identificador-2 quede idéntico a identificador-1, sus PIC deben ser iguales. identificador-1 = campo **emisor**; identificador-2 = campo **receptor** (determina el resultado).
- **Formato 2**: `MOVE literal-1 TO identificador-2`.

Campos emisores posibles: alfabético, numérico, alfanumérico, constante figurativa ZERO, constante figurativa SPACES, elemento de grupo.

```cobol
05 DEPT-OUT            PIC 999.
MOVE 123 TO DEPT-OUT
05 CLASSIFICATION-OUT  PIC X(5).
MOVE "CODE1" TO CLASSIFICATION-OUT
```

## Literales
- **Numéricos**: 1 a 18 dígitos; punto decimal opcional; signo opcional.
- **No numéricos (alfanuméricos)**: 1 a 160 caracteres en COBOL 85 (120 en COBOL 74); cualquier carácter excepto la comilla; van entre comillas simples o dobles.

## Constantes figurativas
Palabras reservadas que representan un valor: **SPACE/SPACES**, **ZERO/ZEROS/ZEROES**.
```cobol
MOVE ZEROS  TO TOTAL-OUT.
MOVE SPACES TO HEADING1.
```

## Objetivos del bloque "Moving Data, Printing Information, Displaying Output"
1. Opciones del MOVE. 2. Reglas para mover campos y literales. 3. Imprimir puntos decimales, signos de moneda y otros símbolos de edición. 4. Diseñar e imprimir informes.

Toda sentencia COBOL de la PROCEDURE DIVISION contiene un **verbo** y generalmente empieza con él.
