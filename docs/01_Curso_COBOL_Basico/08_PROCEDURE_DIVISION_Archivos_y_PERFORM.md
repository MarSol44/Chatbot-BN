---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL PARTE-7.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Parte 7 - Programación estructurada: PROCEDURE DIVISION"
temas: "párrafos, Área A, Área B, OPEN INPUT OUTPUT, READ AT END NOT AT END END-READ, PERFORM UNTIL END-PERFORM, PERFORM simple, PERFORM out-of-line, PERFORM in-line, CLOSE, STOP RUN, programas batch vs interactivos, DISPLAY, ACCEPT"
---

# Parte 7 – Programación estructurada: PROCEDURE DIVISION
_Fuente: COBOL PARTE-7.ppt (30 diapositivas) · Expositor: Ing. Alfredo Asmat_

## Objetivos
Acceder a archivos de entrada/salida, leer datos, hacer MOVE simples, escribir en un archivo de salida, operaciones de fin de trabajo y ejecutar párrafos desde un módulo principal devolviéndole el control.

## Repaso de divisiones
- **IDENTIFICATION DIVISION**: identifica el nombre del programa.
- **ENVIRONMENT DIVISION**: define archivos y equipos usados.
- **DATA DIVISION**:
  - **FILE SECTION**: descripción detallada de registros de entrada/salida.
  - **WORKING-STORAGE SECTION**: entradas por teclado, salidas mostradas y campos necesarios para el proceso que no son parte de registros de E/S.
- **PROCEDURE DIVISION**: leer datos, procesarlos, producir salida y fin de trabajo.
  - Interactivo: aceptar entrada del teclado (ACCEPT), mostrar en pantalla (DISPLAY).
  - Batch: acceder a archivos, leerlos, escribir salida en archivos.

## Párrafos
- La PROCEDURE DIVISION se divide en párrafos; cada uno es un módulo/rutina independiente con instrucciones para un conjunto específico de operaciones.
- **Reglas de nombres de párrafo** (según la diapositiva 9): se codifican en el **Área A** seguidos de punto; siguen las reglas de formación de nombres de datos; deben ser **únicos**. La diapositiva indica que nombres como 1010, 1020, 1030 "no son válidos". _(Aclaración: el estándar COBOL sí permite nombres de párrafo formados solo por dígitos; en la práctica se usan prefijos numéricos como `0000-MAINLINE` o `200-Process-Record`.)_
- **Sentencias**: se codifican en el **Área B**, empiezan con un verbo (READ, MOVE…); la última sentencia del párrafo termina con punto.

## Instrucciones de un programa batch
- **OPEN**: abre los archivos a procesar.
- **PERFORM UNTIL … END-PERFORM**: bucle que lee (READ), procesa e imprime (WRITE) hasta que no haya más registros.
- **CLOSE**: cierra los archivos.
- **STOP RUN**: fin del programa.

## OPEN
```cobol
OPEN INPUT  file-name-1 ...
     OUTPUT file-name-2 ...
```
- Los nombres de archivo deben aparecer en una sentencia **SELECT**.
- El archivo debe abrirse antes de READ o WRITE.
```cobol
OPEN INPUT  Payroll-File
     OUTPUT PayChecks, Err-List
*> o con varias sentencias:
OPEN INPUT  Payroll-File
OPEN OUTPUT PayChecks
OPEN OUTPUT Err-List
```

## PERFORM UNTIL … END-PERFORM
```cobol
PERFORM UNTIL condición-1
    instrucción-1 ...
[END-PERFORM]
```
Repite las instrucciones mientras la condición no se cumpla; cuando se cumple, pasa al END-PERFORM.
```cobol
PERFORM UNTIL WS-More-Data = 'NO'
    READ Payroll-File
        AT END     MOVE 'NO' TO WS-More-Data
        NOT AT END PERFORM 200-Process-Record
    END-READ
END-PERFORM
```
(Asumiendo WS-More-Data = 'YES' inicialmente; el bucle termina cuando se ejecuta `MOVE 'NO' TO WS-More-Data`.)

## READ
```cobol
READ file-name-1
    AT END     instrucción-1 ...
    [NOT AT END instrucción-2 ...]
[END-READ]
```
- Lee **un registro** (no todo el archivo) y lo transfiere al área de entrada.
- El archivo debe figurar en SELECT, FD y OPEN.
- **AT END**: se ejecuta si no hay más registros. **NOT AT END**: se ejecuta si se leyó un registro.

## Tipos de PERFORM
| Tipo | Formato | Comportamiento |
|---|---|---|
| **Simple** | `PERFORM nombre-parrafo` | Ejecuta el párrafo una vez y devuelve el control a la instrucción siguiente. |
| **Out-of-line** | `PERFORM nombre-parrafo UNTIL condición` | Repite el párrafo hasta que se cumpla la condición. |
| **In-line** | `PERFORM UNTIL condición … END-PERFORM` | Repite las instrucciones escritas en línea, sin párrafo aparte. |

## Fin de trabajo
### CLOSE
```cobol
CLOSE file-name-1 ...
CLOSE Payroll-File PayChecks Err-List
*> o
CLOSE Payroll-File
CLOSE PayChecks
CLOSE Err-List
```
Indica que los archivos ya no se necesitan; los libera y desactiva los dispositivos.

### STOP RUN
Termina el programa; suele ser la última instrucción del módulo principal. **Si se omite, la ejecución continúa con el párrafo siguiente.**

## Programas interactivos
- **DISPLAY** para mostrar una pantalla/mensaje de entrada.
- **ACCEPT** guarda los datos en áreas de la WORKING-STORAGE.
- Instrucciones para procesar la entrada.
- DISPLAY para mostrar resultados y para preguntar si hay más entrada; ACCEPT para obtener la respuesta.
