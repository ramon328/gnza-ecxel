# Sincronizador Excel — hojas JULIO y VALORES

Reemplaza la "carpeta anclada del escritorio". Recibe archivos Excel nuevos e
**inserta sus datos en el maestro** (VARIABLES.xlsm), marcando cada fila
insertada con estado **LEÍDO**.

## Estructura esperada

### Maestro (VARIABLES.xlsm)

**JULIO** (hoja obligatoria):
- Columnas: Cliente, Contacto, OT, OC/VIN/PATENTE, Equipamiento, Modelo, CANT, Fecha, [técnicos…]
- Deduplicación por: Cliente + OT + OC/VIN + Equipamiento + Modelo + CANT
- ESTADO se agrega automáticamente en columna V (si no existe)

**VALORES** (hoja obligatoria):
- Empieza en A2 (fila 1 vacía, header en fila 2)
- Columnas: [vacío], DETALLE, OTROS CLIENTES, TATTERSALL Y CL, MITTA, [cálculos…]
- Deduplicación por: DETALLE
- ESTADO se agrega en columna F (si no existe)

### Archivos nuevos

Deben tener las mismas hojas (JULIO / VALORES) con estructura idéntica.

## Cómo funciona

1. **Paso 1:** Sube el maestro (VARIABLES.xlsm con hojas JULIO y VALORES).
2. **Paso 2:** Sube archivos nuevos. Solo se leen hojas llamadas JULIO o VALORES
   (case-insensitive, tildes ignoradas).
   - **JULIO**: Filas nuevas (Cliente/OT no repetidos) se agregan al final, ESTADO=LEÍDO.
   - **VALORES**: Por cada DETALLE, si existe se actualizan valores, si no se agrega. ESTADO=LEÍDO.
3. **Paso 3:** Descarga el maestro actualizado (conserva macros .xlsm).

Cada archivo leído queda registrado en hoja `CONTROL_LECTURAS` con:
- Fecha, nombre archivo, huella SHA-256, hoja, cantidad de filas, estado LEÍDO
- Re-upload detectado automáticamente por huella — se omite si ya fue leído.

## Procesamiento en navegador

Sin servidor, sin Supabase, sin guardar datos. Al recargar, pide subir de nuevo.
Todo cálculo y merge ocurre en el navegador usando [SheetJS](https://sheetjs.com).

## Ejecutar

```bash
python3 -m http.server 8000
# Abre http://localhost:8000/gonza-excel/
```

O deploy en hosting estático (Vercel, Netlify, GitHub Pages, etc.).
