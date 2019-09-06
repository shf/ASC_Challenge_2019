## A routine for preparing mesh in SALOME

Download the software at [SALOME Platform](https://www.salome-platform.org/) 
---
- in the geometry module, import the geometry from file &rarr; import
- create necessary guiding lines to create partitions
- you can use explode to separate different faces
- create necessary sections in the part from Operations &rarr; partition
- go to mesh module
- use create mesh &rarr; triangle: Mefisto
- create group of nodes based on geometry from Mesh &rarr; create group for boundaries and sections
- create wires for edges