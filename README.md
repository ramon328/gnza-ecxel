# Visor 3D — Modelos DWG

Visor web (three.js) para los modelos 3D:

- **Barrera antivuelco — armada** (`models/barrera_armada.obj`): ensamble
  completo según la lámina L1 — arco, patas, placas base, discos baliza,
  pértigas, focos, anclaje y mallas luneta.
- **Enganche Hilux — armado** (`models/enganche_armado.obj`): placas
  laterales, barra 50×50×1040, soporte central, placa y bola de enganche,
  con las dimensiones medidas de las piezas del DWG.
- **Barrera / Enganche — piezas DWG** (`models/barrera.obj`,
  `models/enganche.obj`): las piezas tal como vienen en los DWG
  (escala corregida ÷25.4; los DWG están dibujados en pulgadas).

Ambos armados se generan con `tools_build_armados.py`. Los DWG no contienen
el conjunto montado y sus superficies spline (tramos curvos barridos) usan
referencias ACIS que ningún conversor libre reconstruye completas — por eso
el ensamble se modela paramétrico con las dimensiones de la planimetría.

## Uso

```bash
python3 -m http.server 8000
# abrir http://localhost:8000
```

Controles: rotar (clic izquierdo), pan (clic derecho), zoom (rueda).
Atajos: `F` centrar, `W` alambre, `G` rejilla, `A` ejes, `O` cuadrícula/posición original.
Clic en el nombre de un sólido lo centra; el checkbox lo oculta.
También acepta arrastrar archivos `.stl` / `.obj` al visor.

## Cómo se generaron los modelos

Los DWG guardan los sólidos como ACIS/ShapeManager (formato propietario), no como mallas.
Pipeline de conversión:

1. **ODA File Converter**: DWG 2018 → DXF R2010 (los sólidos quedan como SAT texto inline).
2. **ezdxf**: extracción del SAT de cada entidad `3DSOLID`.
3. **FreeCAD + addon InventorLoader** (headless): SAT → B-rep → teselado a malla OBJ.
4. Postproceso Python: se eliminan componentes degenerados (vértices ±inf y shells
   basura que el importador reconstruye lejos del cuerpo principal de cada sólido).

Nota: la reconstrucción de superficies spline es aproximada. Para fidelidad total,
exportar STEP o STL directamente desde AutoCAD (`STLOUT` / `EXPORT`) y arrastrar el
archivo al visor.
