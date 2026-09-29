---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-3.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 3 - MOVE, salida impresa y en pantalla, edición"
temas: "MOVE entre tamaños distintos, truncamiento, sin redondeo, MOVE de grupo, MOVE múltiple, calificación OF IN, modificación de referencia (inicio:longitud), reportes, títulos, printer spacing chart, supresión de ceros Z"
---

# Parte 3 – MOVE avanzado, salida impresa y supresión de ceros
_Fuente: COBOL PARTE-3.ppt (26 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Receptor MÁS GRANDE que el emisor
| Emisor → Receptor | Instrucción | Resultado | Regla |
|---|---|---|---|
| PIC X(3) → PIC X(5) | `MOVE "abc" TO recv-field` | `abc␣␣` | Relleno con espacios a la derecha |
| PIC 9(3) → PIC 9(5) | `MOVE 123 TO recv-field` | `00123` | Relleno con ceros a la izquierda |
| PIC 9(3)V99 → PIC 9(5)V999 | `MOVE 123.56 TO recv-field` | `00123.560` | Ceros en la parte entera de orden alto y en la parte decimal de orden bajo |

## Receptor MÁS PEQUEÑO que el emisor
| Emisor → Receptor | Instrucción | Resultado | Regla |
|---|---|---|---|
| PIC X(5) → PIC X(3) | `MOVE "abcde" TO recv-field` | `abc` | Truncamiento de orden bajo (derecha) |
| PIC 9(5) → PIC 9(3) | `MOVE 12345 TO recv-field` | `345` | Truncamiento de orden alto (izquierda) |
| PIC 9(5)V999 → PIC 9(3)V99 | `MOVE 12345.678 TO recv-field` | `345.67` | Truncamiento alto y bajo |

**Importante: MOVE no redondea.**

## MOVE de grupo
Un MOVE de grupo se considera **no numérico**: todos los elementos de grupo, incluso con subcampos numéricos, se tratan como alfanuméricos.

## MOVE múltiple
```cobol
MOVE {identificador-1 | literal-1} TO identificador-2 ...
MOVE ZEROS TO Total-Gross Total-Net Total-Taxes
```

## Calificación (nombres repetidos)
Cuando dos datos tienen el mismo nombre se califica con **OF** o **IN**:
```cobol
01 Part-Record.
   05 Part-Number  PIC X(12).
01 Detail-Line.
   05 Part-Number  PIC X(12).

MOVE Part-Number OF Part-Record TO Part-Number OF Detail-Line
```

## Modificación de referencia (extraer parte de un campo)
Sintaxis `campo(inicio:longitud)`:
```cobol
05 Telephone-Number  PIC X(10).     *> contenido: 5633336173
MOVE Telephone-Number (1:3) TO Area-Code   *> 563
MOVE Telephone-Number (4:3) TO Exchange    *> 333
MOVE Telephone-Number (7:4) TO Number      *> 6173
```

## Salida impresa y en pantalla
- La salida en pantalla sirve para consultas rápidas e interactivas sobre el estado de un archivo.
- Los informes impresos son documentos formales; deben ser claros, limpios y fáciles de entender.
- **Espaciado**: líneas a espacio simple, doble, etc.; márgenes superior e inferior; el programa debe detectar el fin de página y pasar a una nueva.
- **Alineación**: a diferencia de los archivos en disco, en los reportes los campos no van contiguos sino espaciados regularmente.
- **Printer spacing chart (tabla de espaciado de impresora)**: ayuda a que (1) las líneas estén bien espaciadas y (2) los campos estén alineados bajo sus encabezados y distribuidos uniformemente. Para pantallas se usa un formulario de diseño de pantalla.
- Ancho típico de línea impresa: **80, 100 o 132** caracteres; en pantalla, 80.

### Tipos de encabezados de un informe
1. **Título del informe**: título, fecha, etc.; puede aparecer una vez al inicio o en cada página.
2. **Título de página**: en cada página; número de página, lista de distribución, etc. (a menudo un solo encabezado cumple ambos roles).
3. **Títulos de columna**: identifican los campos de las líneas siguientes.
Además, **líneas de totales** y saldos al final de página o de informe.

## Supresión de ceros (símbolo Z)
- Ceros no significativos = ceros a la izquierda sin valor significativo (00387 tiene dos).
- Deben omitirse al imprimir: `00387` → `␣␣387`.
- El símbolo de edición **Z** suprime ceros y los reemplaza por espacios.
- Ejemplo: `WS-TOTAL PIC 999` se edita moviéndolo a `TOTAL PIC ZZZ`.

_Nota: la diapositiva 7 ("Normas de la declaración MOVE para elementos elementales") y las comparaciones de salida (diap. 22 y 25) eran imágenes sin texto extraíble._
