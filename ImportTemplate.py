import fenics as fn
from mesh.Importers import MeshImport

ImportedMesh = MeshImport("./UserFiles/MeshUNV.unv")
ImportedMesh.UNVtoXMLConverter()
Edges, Faces = ImportedMesh.MeshGroups()

mesh = fn.Mesh("./UserFiles/mesh.xml")

# Create subdomains
BoundaryEdges = fn.BoundaryMesh(mesh, 'exterior').entity_map(1).array()
BoundaryNodes = fn.BoundaryMesh(mesh, 'exterior').entity_map(0).array()
boundaries=fn.MeshFunction('size_t',mesh,dim=1)
boundaries.set_all(0)
interior={}
idx=1
for key, nodes in Edges.items():
    if all(item in BoundaryNodes for item in nodes):
        for node in nodes:
            ver=fn.Vertex(mesh,node)
            for edge in fn.edges(ver):
                if edge.index() in BoundaryEdges:
                    entity=edge.entities(0)
                    if all(item in nodes for item in entity):
                        boundaries[edge.index()]=idx
        idx+=1
    else:
        interior[key]=nodes

sections=fn.MeshFunction('size_t',mesh,dim=2)
sections.set_all(0)
for num, (key, value) in enumerate(Faces.items(),1):
    for node in value:
        ver=fn.Vertex(mesh,node)
        for cell in fn.cells(ver):
            entity=cell.entities(0)
            if all(item in value for item in entity):
                sections[cell.index()]=num

fn.File("./UserFiles/boundaries.pvd") << boundaries
fn.File("./UserFiles/sections.pvd") << sections
