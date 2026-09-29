---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-4.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 4 - Funciones de edición, débito/crédito, WRITE"
temas: "caracteres de edición . Z $ , * 0 B / CR DB + -, protección de cheques, signo flotante, BLANK WHEN ZERO, campos editados vs no editados, FILLER, WRITE FROM"
---

# Parte 4 – Funciones de edición (DB/CR) y WRITE … FROM
_Fuente: COBOL PARTE-4.ppt (17 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Caracteres de edición
| Carácter | Significado | Carácter | Significado |
|---|---|---|---|
| `.` | Punto decimal real | `B` | Espacio en blanco |
| `Z` | Supresión de ceros | `/` | Barra |
| `$` | Signo de moneda (dólar) | `CR` | Crédito |
| `,` | Coma | `DB` | Débito |
| `*` | Protección de cheques | `+` | Signo más |
| `0` | Cero | `-` | Signo menos |

## Signo de moneda y coma
Se colocan en la posición deseada (igual que el punto decimal), junto con la supresión de ceros, para montos en dólares y centavos.

| PIC emisor | Contenido | PIC receptor | Resultado |
|---|---|---|---|
| 9(4)V99 | 3812^34 | `$9,999.99` | `$3,812.34` |
| 99V99 | 05^00 | `$ZZ.99` | `$ 5.00` |
| 999V99 | 000^05 | `$ZZZ.99` | `$   .05` |
| 9(4)V99 | 0003^82 | `$Z,ZZZ.99` | `$     3.82` |

## Asterisco (protección de cheques)
Se usa en la impresión de cheques o cuando se teme que los importes puedan ser alterados; en otros casos basta con Z.

| PIC emisor | Contenido | PIC receptor | Resultado |
|---|---|---|---|
| 9(3)V99 | 123^45 | `$***.99` | `$123.45` |
| 9(3)V99 | 012^34 | `$***.99` | `$*12.34` |
| 9(5)V99 | 00234^56 | `$**,***.99` | `$***234.56` |

## Débito (DB) y crédito (CR) – aplicaciones contables
En contabilidad un signo menos suele indicar débito o crédito; se usa **DB** o **CR** en lugar del signo menos. Solo aparecen cuando el valor es **negativo**.

| PIC emisor | Contenido | PIC receptor | Resultado |
|---|---|---|---|
| S999 | 123- | `999CR` | `123CR` |
| S999 | 123- | `999DB` | `123DB` |
| S999 | 123+ | `999CR` | `123␣␣` |
| S999 | 123+ | `999DB` | `123␣␣` |

Con signo de moneda flotante:
| PIC emisor | Valor | PIC receptor | Resultado |
|---|---|---|---|
| S9(5) | 98765 | `$$$,999CR` | `$98,765` |
| S9(5) | -98765 | `$$$,999CR` | `$98,765CR` |
| S9(5) | 98765 | `$$$,999DB` | `$98,765` |
| S9(5) | -98765 | `$$$,999DB` | `$98,765DB` |

## Signo más/menos flotante
| PIC emisor | Valor | PIC receptor | Resultado |
|---|---|---|---|
| S9(4) | 1234 | `++,+++` | `+1,234` |
| S9(4) | 0123 | `++,+++` | `+123` |
| S9(4) | -1234 | `++,+++` | `-1,234` |
| S9(4) | 1234 | `--,---` | `1,234` |
| S9(4) | 0123 | `--,---` | `123` |
| S9(4) | -1234 | `--,---` | `-1,234` |
| S9(4) | 1234 | `ZZ,ZZ9+` | `1,234+` |
| S9(4) | -1234 | `ZZ,ZZ9-` | `1,234-` |

## BLANK WHEN ZERO
Si el campo emisor es todo ceros, a veces se prefiere imprimir espacios (en vez de `$.00`, `-0` o un signo suelto, que restan claridad). Se añade `BLANK WHEN ZERO` a la cláusula PIC del campo de reporte.

## Campos editados vs no editados (ejemplo línea de totales)
```cobol
01 TOTAL-LINE.
   05 FILLER            PIC X(8)   VALUE SPACES.
   05 FILLER            PIC X(17)  VALUE 'UNIVERSITY TOTALS'.
   05 FILLER            PIC X(6)   VALUE SPACES.
   05 TOT-TUITION       PIC $$$$,$$9.      *> no editado: PIC 9(6)
   05 FILLER            PIC X(2)   VALUE SPACES.
   05 TOT-UNION-FEE     PIC $$$$,$$9.      *> no editado: PIC 9(4)
   05 FILLER            PIC X      VALUE SPACES.
   05 TOT-ACTIVITY-FEE  PIC $$$$,$$9.      *> no editado: PIC 9(4)
   05 FILLER            PIC X      VALUE SPACES.
   05 TOT-SCHOLARSHIP   PIC $$$$,$$9.      *> no editado: PIC 9(6)
   05 FILLER            PIC X(4)   VALUE SPACES.
   05 TOT-IND-BILL      PIC $$$$,$$9CR.    *> no editado: PIC 9(6)
   05 FILLER            PIC X(47)  VALUE SPACES.
```

## WRITE … FROM
- Los registros a imprimir se definen en la WORKING-STORAGE SECTION (cada uno con su área, y constantes/espacios preasignados con VALUE).
- Esos datos deben pasar al área de impresión (registro de la FILE SECTION) y luego imprimirse.
- `WRITE registro-FILE-SECTION FROM registro-WORKING-STORAGE` reemplaza a un MOVE + WRITE:
```cobol
WRITE PRINT-REC FROM HEADING-1
*> equivale a:
MOVE HEADING-1 TO PRINT-REC
WRITE PRINT-REC
```
