# this code reads the .xml and .unv formats, and mark boundaries
import fenics as fn

def splitter(Str):
    group=[]
    for line in Str:
        temp=line.split()
        if len(temp)>1:
            if temp[1]!='0': group.append(int(temp[1]))
        if len(temp)>4:
            if temp[5]!='0': group.append(int(temp[5]))
    return group


# Import XML mesh into fenics
mesh = fn.Mesh("./MeshImporter/mesh.xml")
# with XDMFFile("mesh.xdmf") as infile:
#     infile.read(mesh)

# reading UNV file to store mesh groups
UNVFile=open("./MeshImporter/MeshUNV.unv","r").readlines()
flag=None
InletStr=[]
OutletStr=[]
WallsStr=[]
InteriorStr=[]
for line in UNVFile:
    if flag=="Inlet":
        InletStr.append(line)
    if flag=="Outlet":
        OutletStr.append(line)
    if flag=="Walls":
        WallsStr.append(line)
    if flag=="Interior":
        InteriorStr.append(line)
    if "Inlet" in line:
        flag="Inlet"
    if "Outlet" in line:
        flag="Outlet"
    if "Walls" in line:
        flag="Walls"
    if "Interior" in line:
        flag="Interior"

inlet=splitter(InletStr)
outlet=splitter(OutletStr)
walls=splitter(WallsStr)
interior=splitter(InteriorStr)

# Create subdomains
BoundaryEdges = fn.BoundaryMesh(mesh, 'exterior').entity_map(1).array()
boundaries=fn.MeshFunction('size_t',mesh,dim=1)
boundaries.set_all(0)
for index in inlet: 
    ver=fn.Vertex(mesh,index)
    for edge in fn.edges(ver):
        if edge.index() in BoundaryEdges:
            entity=edge.entities(0)
            if (entity[0]in inlet) and (entity[1] in inlet):
                boundaries[edge.index()]=1
for index in outlet: 
    ver=fn.Vertex(mesh,index)
    for edge in fn.edges(ver):
        if edge.index() in BoundaryEdges:
            entity=edge.entities(0)
            if (entity[0]in outlet) and (entity[1] in outlet):
                boundaries[edge.index()]=2
for index in walls: 
    ver=fn.Vertex(mesh,index)
    for edge in fn.edges(ver):
        if edge.index() in BoundaryEdges:
            entity=edge.entities(0)
            if (entity[0]in walls) and (entity[1] in walls):
                boundaries[edge.index()]=3
fn.File("./MeshImporter/boundaries.pvd") << boundaries
