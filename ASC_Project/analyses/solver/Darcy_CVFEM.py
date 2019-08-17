import fenics as fe
from mshr import Rectangle, Circle, generate_mesh
import numpy as np
from termcolor import cprint
import time
import copy


__author__ = "Shayan Fahimi, Nasser Arbabi"
__copyright__ = "2019 Shayan Fahimi"
__credits__ = ["Shayan Fahimi, The FEniCS Team"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Shayan Fahimi"
__email__ = "shayan@composites.ubc.ca"
__status__ = "Development"

############################### TIME STEPS #############################
cprint("Creating the time-step size ...", 'blue')

# Time stepping
dt = 0.0 # time step size - determined before each iteration
t = 0.0
numerator = 0 # step number

t_output = 1.0 # steps for requesting output
t_current = t_output # Current time pointer (just for getting output)

cprint("Time-step size asserted successfully.", 'green')

############################# FILE HANDLER #############################
# Files for saving the solution
file_results = fe.XDMFFile("Results/results.xdmf")
file_results.parameters["flush_output"] = True
file_results.parameters["functions_share_mesh"] = True
file_results.parameters["rewrite_function_mesh"] = False

file1 = fe.File('Results/domains.pvd')
file2 = fe.File('Results/boundaries.pvd')
file3 = fe.File('Results/FlowFrontvsTime.pvd')

cprint("File handlers created Successfully.", 'green')
###################### TERMINATION CRITERIA ############################
termination_type = {0:"time-limit", 1:"fill-all", 2:"fill-outlet"}
TEND = 1000 # end time - for halting analysis
max_nofiteration = 10000 # maximum number of iterations for pressure
Number_consecutive_steps = 3 # number of consecutive steps without change in S
min_saturation_change = 1e-3 # minimum saturation change for termination
outlet_filled = False

t_scaling = 1.0 # scaling of first time-step
Saturation_threshold = 0.98 # saturation to add a node as filled node
########################## CREATE MESH #################################
# Create mesh
cprint("\nMESH PRE-PROCESSING", 'blue', attrs=['bold'])
cprint("Creating mesh in FEniCS...", 'blue')

# Size of rectangle
H = 0.1
L = 0.1

# Other geometrical parameters (here just for )
cx = 0.05
cy = 0.05

radius = 0.03

# Number of mesh
nx = 20
ny = 20

# Section thickness
h = 0.1

# Volume Fraction
phi = 0.5

P_inlet = 100000
P_outlet = 0.0

# Create mesh
base = Rectangle(fe.Point(0, 0), fe.Point(L, H))
hole = Circle(fe.Point(cx, cy), radius)
geometry =  base - hole
mesh = generate_mesh(base, nx)
mesh.rename("Current_mesh", "")

coords = mesh.coordinates() # coordination of vertices
num_nodes = mesh.num_vertices() # number of vertices

cprint("Mesh created successfully.", 'green')
################## CELL PROPERTIES INITIALIZATION ###############################
cprint("Initializing cell propeties...", 'blue')
# Create a vector of CV cell volumes
cell_voll = np.zeros(num_nodes) # Volume of CV cells
vertices_on_boundary = set()

for i in range(len(cell_voll)):
    for shared_cell in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim()-2, i)):
        cell_voll[i] = cell_voll[i] + (shared_cell.volume()/3.0)*h*phi

# Create the markers
domains = fe.MeshFunction('size_t', mesh, mesh.topology().dim())
boundaries = fe.MeshFunction('size_t', mesh, mesh.topology().dim() - 1)
vertices = fe.MeshFunction('size_t', mesh, mesh.topology().dim() - 2)

domains.set_all(0)
boundaries.set_all(0)
vertices.set_all(0)
cprint("Cell properties initilized.", 'green')
##################### UNKNOWN SPACES ##################################
cprint("Creating function spaces...", 'blue')

# Define function space
Z = fe.FiniteElement("CG", mesh.ufl_cell(), 2)
Q = fe.FiniteElement("CG", mesh.ufl_cell(), 1)  #saturation
X = fe.VectorElement("CG", mesh.ufl_cell(), 1)

ZZ = fe.FunctionSpace(mesh, Z)
QQ = fe.FunctionSpace(mesh, Q) #saturation function space
XX = fe.FunctionSpace(mesh, X) #saturation function space

# Define test and trial functions
p = fe.TrialFunction(ZZ)
q = fe.TestFunction(ZZ)

# Define vector unknowns
S = np.zeros(num_nodes) # Saturation vector
delta_S = np.zeros(num_nodes) # growth of saturation in one step
V = np.zeros((num_nodes, 2)) # Velocity Vector
FFvsTime = np.zeros(num_nodes)

cprint("Function spaces created successfully.", 'green')
##################### Material properties ##################################
# Define permeability and viscosity
#k = fe.Expression('1.0e-5*exp(-pow((x[1]-0.5-0.05*cos(10*x[0]))/0.2, 2))>= 5e-7 ? 1.0e-5*exp(-pow((x[1]-0.5-0.05*cos(10*x[0]))/0.2, 2)) : 5e-7', degree=1)
k = 1e-10
k_exp = fe.Constant(k)
mu = 0.2
mu_exp = fe.Constant(mu)

cprint("Material properties created Successfully.", 'green')
##################### SOURCE, IC, BC ##################################
# Define source function
g = fe.Constant(0) # body force
w = fe.Constant(0) # pressure difference perpendicular to walls

# Define inlet and outlet
p_inlet_exp = fe.Constant(P_inlet)
p_outlet_exp = fe.Constant(P_outlet)

# Sub domain for walls
class Wall(fe.SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary
wall = Wall()
wall.mark(boundaries, 3)

# Sub domain for inlet gate
class Inlet(fe.SubDomain):
    def inside(self, x, on_boundary):
#        return (x[0] < fe.DOLFIN_EPS and x[1] > 0.03 and x[1]< 0.07) and on_boundary
        return (x[0] < fe.DOLFIN_EPS) and on_boundary

inlet = Inlet()
inlet.mark(boundaries, 1)

class Outlet(fe.SubDomain):
    def inside(self, x, on_boundary):
        return (abs(x[0] - 0.1) < fe.DOLFIN_EPS) and on_boundary
    
outlet = Outlet()
outlet.mark(boundaries, 4)

# Find nodes on the inlet boundary condition
vertices_on_inlet = [facet.entities(0) for facet in fe.SubsetIterator(boundaries, 1)]
vertices_inlet = set() # list of vertices on the inlet

for facet_number,vertices_number in enumerate(vertices_on_inlet):
    for vertice in vertices_number:
        vertices_inlet.add(vertice)

vertices_on_outlet = [facet.entities(0) for facet in fe.SubsetIterator(boundaries, 4)]
vertices_outlet = set() # list of vertices on the outlet

for facet_number,vertices_number in enumerate(vertices_on_outlet):
    for vertice in vertices_number:
        vertices_outlet.add(vertice)

# Set the saturation at the inlet equal to one
for i in vertices_inlet:
    S[i] = 1.0
    FFvsTime[i] = 0.0
    

################## INITIALIZE DOMAIN AND TIME-STEP ##################################
# Book-keeping nodes and facets
available_nodes = set() # nodes in the domain
available_cells = set() # cells of the domain
nodes_on_flow_front = set() # nodes on the flow front
facet_on_flow_front = set() # facets on the flow front

# populating nodes on the domain
for i in set(range(num_nodes)) - available_nodes:
    if S[i]>0:
        available_nodes.add(i)

# populating nodes and facets on the flow front and set marker = 2
# populating cells in the domain
# set domain marker for available cells 1
for i in available_nodes:
    for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim()-2, i)):
        available_cells.add(c.global_index())
        domains[c] = 1
        for vertice in fe.vertices(c):
            if vertice.index() not in available_nodes:
                nodes_on_flow_front.add(vertice.global_index())
                vertices[vertice] = 2

for i in available_cells:
    for e in fe.facets(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
            if e.entities(0)[0] in nodes_on_flow_front and e.entities(0)[1] in nodes_on_flow_front:
                facet_on_flow_front.add(e.global_index())
                boundaries[e] = 2

# boundary condition for gate
bc1 = fe.DirichletBC(ZZ, p_inlet_exp, boundaries, 1)
      
# boundary condition for flow-front
bc2 = fe.DirichletBC(ZZ, p_outlet_exp, boundaries, 2)

# boundary condition for outlet
bc3 = fe.DirichletBC(ZZ, p_outlet_exp, boundaries, 4)

# a) set BC and Domain in each step
# Domain
dx_domain = fe.Measure('dx')(subdomain_data=domains)
ds_wall = fe.Measure("ds")(subdomain_data=boundaries)

# b) variational problem and computing pressure
a = fe.inner(k_exp/mu_exp*fe.grad(p), fe.grad(q))*dx_domain(1) + p*q*dx_domain(0)
L = g*q*dx_domain(1) + w*q*ds_wall(3) + g*q*dx_domain(0)
ph = fe.Function(ZZ)
fe.solve(a == L, ph, [bc1, bc2, bc3])
ph.rename("Pressure", "")

# b) postprocess velocity
uh = fe.project(-k_exp/mu_exp*fe.grad(ph), XX)
d2v = fe.dof_to_vertex_map(XX)
for i in range(len(V)):
    V[int(d2v[2*i]/2), 0] = uh.vector()[2*i]
    V[int(d2v[2*i]/2), 1] = uh.vector()[2*i+1]
uh.rename("velocity", "")

sh = fe.Function(QQ)
ffvstimeh = fe.Function(QQ)
sh.rename("Saturation", "")
ffvstimeh.rename("FlowfrontvsTime", "")
v2d = fe.vertex_to_dof_map(QQ)
for i in range(len(S)):
    sh.vector()[v2d[i]] = S[i]

# plot solution and write output file
file_results.write(ph, t)
file_results.write(uh, t)
file_results.write(sh, t)

# find the time-step to fill one CV
dt = TEND 

for i in available_cells:
    for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
        cell_midpoint = (coords[c.entities(0)[0]]+coords[c.entities(0)[1]]+coords[c.entities(0)[2]])/3.0
        for v_i in c.entities(0):
            if S[v_i] < 1.0:
                for v_j in c.entities(0):
                    if v_j in vertices_inlet:
                        coord_i = coords[v_i]
                        coord_j = coords[v_j]
                        edge_midpoint = (coord_i + coord_j)/2.0
                        norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                        normal = [-(cell_midpoint[1] - edge_midpoint[1]), (cell_midpoint[0] - edge_midpoint[0])]/norm
                        distance = np.linalg.norm([(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])])
                        inward_normal = [(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])]/distance

                        if np.dot(inward_normal, normal) < 0:
                            normal = [cell_midpoint[1] - edge_midpoint[1], -(cell_midpoint[0] - edge_midpoint[0])]/norm

                        vel = (V[v_i] + V[v_j])/2.0
                        flux = np.dot(vel, normal)*norm*h
                        dt = min(dt, (1 - S[v_i])*(cell_voll[v_i])/abs(flux))
    
dt = t_scaling*dt

################## SOLVING IN TIME ##################################
while (t < fe.DOLFIN_EPS + TEND):

    delta_S.fill(0)

    # Find fill factor for predicted time-step
    for i in available_cells:
        for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
            cell_midpoint = (coords[c.entities(0)[0]]+coords[c.entities(0)[1]]+coords[c.entities(0)[2]])/3.0
            for v_i in c.entities(0):
                if S[v_i] < 1.0:
                    for v_j in c.entities(0):
                        if v_j != v_i:
                            coord_i = coords[v_i]
                            coord_j = coords[v_j]
                            edge_midpoint = (coord_i + coord_j)/2.0
                            norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                            normal = [-(cell_midpoint[1] - edge_midpoint[1]), cell_midpoint[0] - edge_midpoint[0]]/norm
                            distance = np.linalg.norm([(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])])
                            inward_normal = [(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])]/distance

                            if np.dot(inward_normal, normal) < 0:
                                normal = [cell_midpoint[1] - edge_midpoint[1], -(cell_midpoint[0] - edge_midpoint[0])]/norm
    
                            vel = (V[v_i] + V[v_j])/2.0
                            flux = np.dot(vel, normal)*norm*h
                            delta_S[v_i] = delta_S[v_i] + dt*(abs(flux))/(cell_voll[v_i])

    # Finding dt to fill just one control volueme
    dt_new = dt

    max_s = max(S + delta_S)

    if max_s > 1:
        for i in range(num_nodes):
            if delta_S[i] != 0 and S[i] + delta_S[i] > 1.0:
                dt_new = min(dt_new, (dt*(1.0 - S[i])/(delta_S[i])))
    elif max_s == 1:
        for i in range(num_nodes):
            if delta_S[i] != 0 and S[i] + delta_S[i] < 1.0:
                dt_new = max(dt_new, (dt*(1.0 - S[i])/(delta_S[i])))
    else:
        raise

    SS = copy.deepcopy(S)
    SS_delta = copy.deepcopy(delta_S)

    for i in range(num_nodes):
        if delta_S[i] != 0.0:
            delta_S[i] = (delta_S[i])*dt_new/dt
            S[i] = S[i] + delta_S[i]

    # Check if the saturation is changed more than a threshhold 
    if np.amax(delta_S) < min_saturation_change:
        termination_para += 1
    else:
        termination_para = 0

    # Check if the outlet is filled
    Outlet_filled = True
    for i in vertices_outlet:
        if S[i] < Saturation_threshold:
            Outlet_filled = False

    t += dt_new

    # print for the user
    for i in available_cells:
        for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
            for v_i in c.entities(0):
                sh.vector()[v2d[v_i]] = S[v_i]

    # finding available cells and time-step for next step
    unfilled_nodes = set()
    nodes_on_flow_front = set()

    boundaries.set_all(0)
    vertices.set_all(0)

    available_nodes_old = copy.deepcopy(available_nodes)
    available_cells_old = copy.deepcopy(available_cells)

    for i in set(range(num_nodes)) - available_nodes:
        if S[i] > Saturation_threshold:
            available_nodes.add(i)
        if S[i] < Saturation_threshold:
            unfilled_nodes.add(i)

    for i in available_nodes - available_nodes_old:
        for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim()-2, i)):
            available_cells.add(c.global_index())
            domains[c] = 1

    for c in available_cells:
        for vertice in fe.vertices(fe.MeshEntity(mesh, mesh.topology().dim(), c)):
            if vertice.index() not in available_nodes:
                nodes_on_flow_front.add(vertice.global_index())
                vertices[vertice] = 2

    if available_nodes_old != available_nodes:
        for i in available_nodes - available_nodes_old:
            FFvsTime[i] = t

    if unfilled_nodes == set():
        cprint('All CVs are filled!', 'green')
        for i in range(len(FFvsTime)):
            ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
        file3 << ffvstimeh
        break
    elif numerator == max_nofiteration:
        cprint('Maximum iteration number' + str(max_nofiteration) + ' is reached!', 'green')
        for i in range(len(FFvsTime)):
            ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
        file3 << ffvstimeh
        break
    elif termination_para > Number_consecutive_steps:
        cprint('Saturation halted for' + str() + 'iterations!', 'green')
        for i in range(len(FFvsTime)):
            ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
        file3 << ffvstimeh
        break
    elif Outlet_filled == True:
        cprint('All outlet nodes are filled!', 'green')
        for i in range(len(FFvsTime)):
            ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
        file3 << ffvstimeh
        break

    facet_on_flow_front = set()

    # Sub domain for walls
    wall.mark(boundaries, 3)

    for i in available_cells:
        for e in fe.facets(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
            if e.entities(0)[0] in nodes_on_flow_front and e.entities(0)[1] in nodes_on_flow_front:
                facet_on_flow_front.add(e.global_index())
                boundaries[e] = 2

    # Sub domain for inlet gate
    inlet.mark(boundaries, 1)

    # Sub domain for outlet
    outlet.mark(boundaries, 4)

#   Check if the domain is change to solve for pressure
    if available_cells_old != available_cells:
        numerator += 1
        cprint('\nSOLUTION OF THE LINEAR PROBLEM', 'blue', attrs=['bold'])
        cprint('\nStep: ' + str(numerator) + ', time:' + str(t), 'blue')

        # boundary condition for gate
        bc1 = fe.DirichletBC(ZZ, p_inlet_exp, boundaries, 1)

        # boundary condition for flow front
        bc2 = fe.DirichletBC(ZZ, p_outlet_exp, boundaries, 2)

        # boundary condition for outlet
        bc3 = fe.DirichletBC(ZZ, p_outlet_exp, boundaries, 4)

        # set BC and Domain in each step
        # Domain
        dx_domain = fe.Measure('dx')(subdomain_data=domains)
        ds_wall = fe.Measure("ds")(subdomain_data=boundaries)
        
        # variational problem and computing pressure
        a = fe.inner(k_exp/mu_exp*fe.grad(p), fe.grad(q))*dx_domain(1) + p*q*dx_domain(0)
        L = g*q*dx_domain(1) + w*q*ds_wall(3) + g*q*dx_domain(0)

        ph = fe.Function(ZZ)

        fe.solve(a == L, ph, [bc1, bc2, bc3])
        ph.rename("Pressure", "")

        # postprocess velocity
        uh = fe.project(-k_exp/mu_exp*fe.grad(ph), XX)
        d2v = fe.dof_to_vertex_map(XX)
        for i in range(len(V)):
            V[int(d2v[2*i]/2), 0] = uh.vector()[2*i]
            V[int(d2v[2*i]/2), 1] = uh.vector()[2*i+1]

        uh.rename("velocity", "")
    
    # plot solution and write output file
    if t > t_current:
#        file_results.write(ph, t)
#        file_results.write(uh, t)
        file_results.write(sh, t)

#        t_current = t_output + t

#        file1 << (domains, t)
#        file2 << (boundaries, t)