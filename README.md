# Visor 3D — Modelos DWG

Visor web (three.js) para los 10 productos, cada uno en versión **armada**
y **piezas DWG**:

- Barra exterior 6M (arco, patas, placas, discos baliza, pértigas, focos,
  anclaje y malla luneta según la lámina L1)
- Barras interiores: Hilux, L200, Colorado, GWM POER
- Enganches: Hilux, L200
- Portarruedas: Kitcar, Mitta, Tipo T (con neumático de referencia)

Los armados se generan con `tools_build_armados.py`. Los DWG no contienen
los conjuntos montados (las piezas vienen dispersas como lámina de despiece)
y sus tramos de tubo curvo usan superficies spline con referencias ACIS que
ningún conversor libre reconstruye — por eso los ensambles se modelan
paramétricos con las dimensiones de la planimetría y de las piezas. Las
vistas "piezas" muestran los sólidos reales de cada DWG (escala corregida:
varios archivos están dibujados a 25.4:1, en pulgadas).

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
