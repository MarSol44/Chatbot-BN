---
documento: "Curso COBOL Básico - Banco de la Nación"
archivo_original: "COBOL Introduccion.ppt"
expositor: "Ing. Alfredo Asmat"
modulo: "Introducción"
temas: "historia de COBOL, CODASYL, DoD, Grace Hopper, 4 divisiones, PICTURE, compiladores, aplicaciones en producción, escasez de coboleros"
---

# Introducción al lenguaje COBOL
_Fuente: COBOL Introduccion.ppt (18 diapositivas) · Expositor: Ing. Alfredo Asmat_

## ¿Qué es COBOL?
- **COBOL** = *COmmon Business Oriented Language* (Lenguaje Común Orientado a Negocios).
- Hacia 1980, y todavía hoy, el lenguaje por excelencia para programar los mainframes de IBM es COBOL.
- Muchos profesionales hacen mantenimiento a aplicaciones escritas en COBOL, aunque casi no se enseña en centros de estudios superiores.

## Historia
- Se definió en **1960**, impulsado por el **DoD** (Department of Defense de EE. UU.).
- Motivo: cada sistema que el DoD compraba o subcontrataba venía escrito en un lenguaje distinto (casi siempre ensambladores dependientes de la máquina, p. ej. NEAT/3 de NCR), lo que generaba grandes gastos para mantener sistemas heterogéneos.
- El DoD participó en el diseño; el proceso duró menos de un año y, en pocos años, obligó a que todos los sistemas de gestión instalados en el DoD estuvieran escritos en COBOL.
- El comité se constituyó dentro de **CODASYL**; su alma máter fue **Grace Hopper** (US Navy), diseñadora de **Flow-Matic**.
- Poder programar en COBOL se usó como argumento de marketing para vender ordenadores.
- Fortran siguió usándose en entornos científicos/ingenieriles; en aplicaciones de negocio (contabilidad, facturas, proveedores) se impuso COBOL.
- **Ada** (otro lenguaje promovido por el DoD) nunca fue muy usado comercialmente; el DoD dejó de exigirlo en 1997.

## Estructura de un programa COBOL
COBOL organiza el programa en **Divisiones → Secciones → Párrafos** (a diferencia de Fortran, donde se puede definir cualquier cosa en cualquier punto). Hay cuatro divisiones, siempre en este orden:

| División | Para qué sirve |
|---|---|
| **IDENTIFICATION DIVISION** | Información de identificación del programa: nombre, autor(es), fecha de escritura, etc. Sirve más bien a título de comentario. |
| **ENVIRONMENT DIVISION** | Información de entrada/salida: qué ficheros usa el programa, cómo son (secuenciales, indexados, etc.), cómo se llaman para el programa y cómo se llaman realmente en el sistema. |
| **DATA DIVISION** | Definición de los datos: registros de ficheros (**FILE SECTION**), áreas de trabajo (**WORKING-STORAGE SECTION**) y, si es un módulo llamado por otro programa, áreas de intercambio (**LINKAGE SECTION**). Es "el reino de la PICTURE". |
| **PROCEDURE DIVISION** | Las instrucciones del programa: lecturas y escrituras (READ, WRITE), movimientos (MOVE), cálculos (ADD, MULTIPLY, DIVIDE, SUBTRACT), llamadas a rutinas (CALL) hasta el **STOP RUN**, salvo que antes ocurra una cancelación por error lógico, aritmético o de datos de entrada. |

## Codificación
- El **punto** indica el fin de la frase: fin de sentencia o de párrafo.
- Principal ventaja: **autodocumentación**; escribir COBOL es casi como describir en inglés lo que hay que hacer.
- Gestión de ficheros potente y sencilla.
- La cláusula **PICTURE** (abreviada siempre **PIC** por los "coboleros") es excelente para definir datos.

## Evolución y entornos
- COBOL se adaptó a bases de datos (IMS/DL1, Total, Adabas, DB2), gestores de teleproceso (IMS/DC, CICS) y otros sistemas operativos (UNIX, Linux), aunque no tanto al mundo PC.
- Existen compiladores COBOL para PC desde mediados/finales de los 80 y entornos de simulación del mainframe (compilador, CICS, IMS, DB2, debugger, incluso rutinas Assembler).

## Aplicaciones COBOL en producción
- Muchas aplicaciones llevan 20 años o más en producción y sufren cambios por: cambios legales, nuevas necesidades de la compañía, nuevos productos.
- Esos cambios obligan a modificar uno, varios o todos los programas; es clave entender rápido la funcionalidad de un programa, localizar dónde modificarlo y que funcione según las nuevas especificaciones.

## Escasez de "coboleros" y riesgo para la industria financiera
- Las universidades prácticamente ya no enseñan COBOL → poca oferta de especialistas.
- Esto impacta sobre todo a la industria financiera, que aún lo usa.
- Preguntas planteadas en el curso: ¿hay riesgos?, ¿deben las instituciones reincorporarlo?, ¿cómo solucionan los bancos una falla en aplicaciones COBOL?
