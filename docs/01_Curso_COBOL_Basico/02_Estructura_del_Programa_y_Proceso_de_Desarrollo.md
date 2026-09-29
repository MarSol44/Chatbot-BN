---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-1.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 1 - Estructura del lenguaje COBOL"
temas: "divisiones, Hello World, proceso de desarrollo, elementos de grupo, diagramas de flujo, pseudocódigo, compilación, depuración, programación estructurada, JCL, DB2, CICS, EXEC SQL, EXEC CICS"
---

# Parte 1 – Estructura del lenguaje COBOL
_Fuente: COBOL PARTE-1.ppt (25 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Las cuatro divisiones (orden fijo)
1. **IDENTIFICATION DIVISION**: información sobre el programa para el programador y el compilador.
2. **ENVIRONMENT DIVISION**: describe el ambiente en el que se ejecutará el programa.
3. **DATA DIVISION**: descripciones de los elementos de datos procesados.
4. **PROCEDURE DIVISION**: código que manipula los datos; aquí se describe el algoritmo.

Algunos compiladores exigen las cuatro divisiones; otros solo IDENTIFICATION y PROCEDURE.

## Ejemplo "Hello World"
```cobol
000100 IDENTIFICATION DIVISION.
000200 PROGRAM-ID. HELLOWORLD.
000300
000400 ENVIRONMENT DIVISION.
000500 CONFIGURATION SECTION.
000600 SOURCE-COMPUTER. IBM-COBOL.
000700 OBJECT-COMPUTER. IBM-COBOL.
000800
000900 DATA DIVISION.
001000 FILE SECTION.
001100
101200 PROCEDURE DIVISION.
101300
101400 MAIN-LOGIC.
101500      DISPLAY "Hello world!"
101600      STOP RUN.
```

## Proceso de desarrollo de programas
1. Determinar las especificaciones del programa.
2. Diseñar el programa usando herramientas de planificación.
3. Codificar el programa fuente (editor).
4. Compilar el programa.
5. Probar el programa (test).
6. Documentar el programa.

**Especificaciones del programa** incluyen:
- *Record layout forms*: formatos de diseño de registro para describir entrada y salida.
- *Printer spacing charts*: plantillas de espaciado para la salida impresa.

**Especificaciones de entrada/salida**: nombres de registros y campos, tamaños y tipos de datos. Se usan para construir la DATA DIVISION. Ejemplo (Registro de nómina):

| Campo | Tipo | Tamaño |
|---|---|---|
| Nombre | Alfanumérico | 30 |
| Dirección | Alfanumérico | 23 |
| Pay-Rate | Numérico | 5.2 (longitud 7 con 2 decimales) |

## Elementos de grupo
- Son el equivalente COBOL de las **estructuras**.
- Se componen de elementos elementales u otros grupos; en última instancia todo se define con elementos elementales.
- La jerarquía se representa con **números de nivel**.
```cobol
01  DATE-CPU.
    02  YEAR-CPU     PIC 99.
    02  MONTH-CPU    PIC 99.
    02  DAY-CPU      PIC 9(2).
```

## Herramientas de diseño
- **Flowchart (diagrama de flujo/bloques)**: representación gráfica de la lógica. Ejemplo: Student-File (INPUT) → PROCESSING → Attendance Report (OUTPUT).
- **Pseudocódigo**: expresiones tipo inglés que representan la lógica. Ejemplo:
```
Initialization:  Open files / Read first record / Write heading
Processing:
PERFORM UNTIL FIN-ARCHIVO = 1
    IF NRO-CREDITOS > 20
        Write students name
    END-IF
    Read record AT END MOVE 1 TO FIN-ARCHIVO END-READ
END-PERFORM
Termination:     Close files / Stop
```
- **Descripción de archivo**: campos (datos) → registros (conjunto de campos). Ej.: Name, Credits, Major (John Adams 90 Political Science; Amelia Earhart 120 Aviation; Orville Wright 115 Engineering; Georgia O'Keeffe 125 Art).

## Codificación, compilación y pruebas
- La codificación se hace **solo después** de especificar completamente los requisitos y planificar la lógica.
- El **compilador** revisa el fuente; un **error de sintaxis** ocurre al infringir una regla de programación.
- **Pruebas/depuración**: errores de ejecución →
  - *Error lógico*: produce resultados incorrectos.
  - *Violación del sistema operativo*: provoca la terminación del programa.
- **Documentación**: manuales de procedimientos para usuarios y operadores.

## Técnicas de depuración
- **Chequeo de escritorio**: revisar el programa antes y después de codificarlo.
- **Corrección de errores de sintaxis**: usar el listado fuente impreso/mostrado con los mensajes de diagnóstico.

## Mejorar el diseño: programación estructurada y top-down
- **Programación estructurada**: elimina el uso de **GO TO** (saltos sin regreso al punto de partida); la lógica es más fácil de seguir usando **PERFORM**.
- El programa se divide en **párrafos**; el párrafo/módulo principal controla el flujo con PERFORM y llama a otros módulos cuando se necesitan.
- Cada módulo puede escribirse y probarse de forma independiente.

## Control de procesos en mainframe
- **JCL (Job Control Language)**: lenguaje de secuencias de comandos de los sistemas operativos mainframe IBM que indica al subsistema de entrada (JES2 o JES3) cómo ejecutar un programa batch o iniciar un subsistema. Actúa como conductor/planificador de los programas COBOL batch. (Ver detalle en la Guía TSO, Tema 2: JCL.)
- **DB2**: sistema gestor de bases de datos relacionales de IBM; actúa como base de datos backend para programas COBOL.
- **CICS (Customer Information Control System)**: servidor de transacciones de mainframe IBM; controlador e interfaz de usuario para programas COBOL en línea. Soporta miles de transacciones por segundo. Programable en COBOL, PL/I, C, C++, ensamblador, REXX y Java.
  - Cada programa CICS se inicia con un **ID de transacción**.
  - Las pantallas CICS se envían como **mapas**; el usuario ingresa datos que el programa recibe desde el mapa. Pueden tener texto resaltado, colores o parpadeo.

### Ejemplo SQL embebido (DB2)
```cobol
EXEC SQL
    SELECT  TKT_NUM, TKT_ISS_DTE, MEMO_NUM, MEMO_CRTN_DTE,
            WVR_CDE, WVR_CRTN_DTE
      INTO  :WVU0140A-TKT-NUM
           ,:WVU0140A-TKT-ISS-DTE
           ,:WVU0140A-MEMO-NUM
           ,:WVU0140A-MEMO-CRTN-DTE :WSW-NULL-INDICATOR
           ,:WVU0140A-WVR-CDE
           ,:WVU0140A-WVR-CRTN-DTE
      FROM  T_WVR
     WHERE  TKT_NUM = :W400-PRMY-TKT-NUM
      WITH UR
END-EXEC.
```

### Ejemplo envío de mapa CICS
```cobol
EXEC CICS
    SEND MAPSET(MPS1) MAP(MP1)
END-EXEC
```
