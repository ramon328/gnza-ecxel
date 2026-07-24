# Visor 3D — Modelos DWG

Visor web (three.js) para los modelos 3D:

- **Barrera antivuelco — armada** (`models/barrera_armada.obj`): ensamble
  reconstruido paramétricamente según la planimetría (arco + patas + placas
  base + discos baliza). Los DWG solo contienen las piezas sueltas de
  fabricación, no el conjunto armado.
- **Barrera — piezas** (`models/barrera.obj`, 12 sólidos)
- **Enganche Hilux — piezas** (`models/enganche.obj`, 11 sólidos)

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
