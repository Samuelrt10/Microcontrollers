import cadquery as cq

# Dimensiones en mm
diametro_exterior = 80.0
espesor_base = 10.0
diametro_cilindro = 40.0
altura_cilindro = 30.0
barreno_central = 20.0
diametro_pernos = 6.0
radio_distribucion_pernos = 30.0

# Modelado paramétrico
pieza = (
    cq.Workplane("XY")
    .circle(diametro_exterior / 2)
    .extrude(espesor_base)
    .faces(">Z")
    .workplane()
    .circle(diametro_cilindro / 2)
    .extrude(altura_cilindro)
    .faces(">Z")
    .hole(barreno_central)
    # Patrón circular de barrenos para pernos en la base
    .faces("<Z[1]")
    .workplane()
    .polarArray(radio_distribucion_pernos, 0, 360, 4)
    .circle(diametro_pernos / 2)
    .cutThruAll()
)

# Exportación directa a STEP
cq.exporters.export(pieza, "pieza_mecanica.step")