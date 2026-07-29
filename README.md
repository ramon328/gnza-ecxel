# Sincronizador Excel — hojas JULIO y VALORES

Web que reemplaza la "carpeta anclada del escritorio": recibe archivos Excel
nuevos y **inserta sus datos en el maestro** (VARIABLES … .xlsm), marcando cada
fila insertada con estado **LEÍDO**.

## Cómo funciona

1. **Subir el maestro** (el Excel VARIABLES con las hojas JULIO y VALORES).
2. **Subir archivos nuevos** — solo se leen las hojas cuyo título sea
   `JULIO` o `VALORES` (mayúsculas/tildes indiferentes).
   - **JULIO**: las filas nuevas (Cliente/OT no repetidos) se agregan al final
     y se marcan `LEÍDO` en la columna ESTADO.
   - **VALORES**: cada fila se busca por DETALLE; si existe se actualizan sus
     valores, si no existe se agrega. También queda `LEÍDO`.
3. **Descargar** el maestro actualizado (conserva las macros .xlsm).

El control de "qué ya se leyó" vive dentro del propio Excel, en la hoja
`CONTROL_LECTURAS` (fecha, archivo, huella SHA-256, hoja, filas, estado).
Si se vuelve a subir un archivo ya leído, el sistema lo detecta por su huella
y lo omite.

## Sin servidor, sin base de datos

Todo se procesa en el navegador con [SheetJS](https://sheetjs.com). No hay
Supabase ni almacenamiento: al recargar la página siempre se pide subir los
archivos de nuevo, tal como se solicitó.

## Uso

```bash
python3 -m http.server 8000
# abrir http://localhost:8000/gonza-excel/
```

O publicar la carpeta `gonza-excel/` en cualquier hosting estático.
