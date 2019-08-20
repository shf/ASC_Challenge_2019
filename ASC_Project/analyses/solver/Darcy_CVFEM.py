import fenics as fe
import numpy as np
import time
import logging
import copy
import sys
import os

__all__ = ['Darcy_CVFEM']

#__author__ = "Shayan Fahimi, Nasser Arbabi"
#__copyright__ = "2019 Shayan Fahimi"
#__credits__ = ["Shayan Fahimi, The FEniCS Team"]
#__license__ = "GPL"
#__version__ = "1.0"
#__maintainer__ = "Shayan Fahimi"
#__email__ = "shayan@composites.ubc.ca"
#__status__ = "Development"

class Darcy_CVFEM():
    'Converting user input to an input file for FEniCS'

    def __init__(self, input):
        _data_handling = input['analysis']
#        _ICs = input['ICs']
        _resin = input['resin']
        _sections = input['sections']
#        _sec = input['sections']
        _inlets = input['BCs']['inlets']
        _outlets = input['BCs']['outlets']
        _edges = input['BCs']['edges']
#        _walls = input['BCs']['Walls']
#        _Loads = input['loads']
        _step = input['step']
        
        self._logging(_data_handling)
        self._create_output_files(_data_handling)
        self._define_resin(_resin)
        self._define_sections(_sections)
        self._mesh_initialization(_data_handling)
        self._define_function_space(self._mesh)
#        self._define_functions(_ICs)
        self._define_step(_step)
        self._define_BCs(_inlets, _outlets, _edges)
#        self._define_loads(_Loads)
#        self.SolverConfig(_steps, _output)
        return None

    def _logging(self, _data_handling):
        directory = _data_handling['folder_address'] + "/results/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        logging.basicConfig(level=logging.DEBUG, filename=directory + "debug.log" , filemode="a+",
            format="%(asctime)-15s %(levelname)-8s %(message)s")
        logging.info("The analysis has been submitted") 

        self._message_file = open(directory + "analysis.msg", "w")

    def _create_output_files(self, _data_handling):
        '''
        Create output files to store the analysis results
        '''
        # Files for saving the solution
        self._resultsfile = fe.XDMFFile(_data_handling['folder_address'] + "/results/analysis.xdmf")
        self._resultsfile.parameters["flush_output"] = True
        self._resultsfile.parameters["functions_share_mesh"] = True
        self._resultsfile.parameters["rewrite_function_mesh"] = False

        self._domainfile = fe.File(_data_handling['folder_address'] + "/results/domains.pvd")
        self._boundaryfile = fe.File(_data_handling['folder_address'] + "/results/boundaries.pvd")
        self._flowfrontfile = fe.File(_data_handling['folder_address'] + "/results/flowfrontvstime.pvd")

        self._message_file.write("File handlers created Successfully.\n")

    def _define_resin(self, _resin):

        self._mu_exp = fe.Constant(_resin['viscosity'])
        self._message_file.write("Resin material (viscosity = "+  str(_resin['viscosity']) + ") created successfully. \n")

    def _define_sections(self, _sections):

        self._k_exp = {}
        self._h = {}
        self._phi = {}
        self._message_file.write("Creating Sections ... \n")
        for section_id in _sections.keys():
            self._k_exp[section_id] = fe.as_matrix(((_sections[section_id]['K11'], _sections[section_id]['K12'])
            , (_sections[section_id]['K12'], _sections[section_id]['K22'])))
            self._h[section_id] = _sections[section_id]['thickness']
            self._phi[section_id] = _sections[section_id]['volume_fraction']
            self._message_file.write("Section number: " + str(section_id) + "\n")
            self._message_file.write("Section permeability: " + str(self._k_exp[section_id]) + "\n")
            self._message_file.write("Section thickness: " + str(self._h[section_id]) + "\n")
            self._message_file.write("Section volume fraction: " + str(self._phi[section_id]) + "\n")

        self._message_file.write("Section material created successfully. \n")

    def _mesh_initialization(self, _data_handling):

        '''
        Initializing the mesh and setting the number of nodes and cells and
        cell volumes
        '''
        # Create mesh
        self._message_file.write("\nMESH PRE-PROCESSING \n")
        self._message_file.write("Creating mesh in FEniCS... \n")

        self._mesh = fe.Mesh(_data_handling['folder_address'] + "/mesh.xml")
        self._mesh.rename("Current_mesh", "")

        self._coords = self._mesh.coordinates() # coordination of vertices
        self._num_nodes = self._mesh.num_vertices() # number of vertices

        self._cell_voll = np.zeros(self._num_nodes) # Volume of CV cells

        for i in range(len(self._cell_voll)):
            for shared_cell in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim()-2, i)):
                self._cell_voll[i] = self._cell_voll[i] + (shared_cell.volume()/3.0)*self._h[0]*self._phi[0]

        # Create the markers
        self._BoundaryEdges = fe.BoundaryMesh(self._mesh, 'exterior').entity_map(1).array()
        self._BoundaryNodes = fe.BoundaryMesh(self._mesh, 'exterior').entity_map(0).array()

        self._domains = fe.MeshFunction('size_t', self._mesh, self._mesh.topology().dim())
        self._boundaries = fe.MeshFunction('size_t', self._mesh, self._mesh.topology().dim() - 1)
        self._vertices = fe.MeshFunction('size_t', self._mesh, self._mesh.topology().dim() - 2)

        self._domains.set_all(0)
        self._boundaries.set_all(0)
        self._vertices.set_all(0)

        self._message_file.write("Mesh created successfully. \n")

    def _define_function_space(self, _mesh):
        '''
        Define function spaces for the Darcy Problem
        '''
        self._message_file.write("Creating function spaces... \n")

        # Define function space
        _Z = fe.FiniteElement("CG", _mesh.ufl_cell(), 2)
        _Q = fe.FiniteElement("CG", _mesh.ufl_cell(), 1)  #saturation
        _X = fe.VectorElement("CG", _mesh.ufl_cell(), 1)

        self._ZZ = fe.FunctionSpace(_mesh, _Z)
        self._QQ = fe.FunctionSpace(_mesh, _Q) #saturation function space
        self._XX = fe.FunctionSpace(_mesh, _X) #saturation function space

        # Define test and trial functions
        self._pre_test_function = fe.TrialFunction(self._ZZ)
        self._pre_trial_function = fe.TestFunction(self._ZZ)

        # Define vector unknowns
        self._saturation = np.zeros(self._num_nodes) # Saturation vector
        self._delta_saturation = np.zeros(self._num_nodes) # growth of saturation in one step
        self._vel = np.zeros((self._num_nodes, 2)) # Velocity Vector
        self._FFvsTime = np.zeros(self._num_nodes)

        self._message_file.write("Function spaces created successfully. \n")

    def _define_step(self, _step):

        'Defining the step initilization and handling parameters'
        self._message_file.write("Creating the time-step size ... \n")

        # Time stepping
        self._dt = 0.0 # time step size - determined before each iteration
        self._t = 0.0
        self._numerator = 0 # step number

        self._output_steps = _step['output_steps'] # steps for requesting output
        self._current_output_step = self._output_steps # Current time pointer (just for getting output)

        self._message_file.write("Time-step size asserted successfully.\n")

#        self._termination_type = {0:"time-limit", 1:"fill-all", 2:"fill-outlet"}
        self._TEND = _step['termination_time'] # end time - for halting analysis
        self._max_nofiteration = _step['maximum_itrations'] # maximum number of iterations for pressure
        self._Number_consecutive_steps = _step['maximum_consequtive_steps'] # number of consecutive steps without change in S
        self._min_saturation_change = _step['minimum_change_of_saturation'] # minimum saturation change for termination
        self._outlet_filled = False

        self._t_scaling = _step['time_scaling_parameter'] # scaling of first time-step
        self._Saturation_threshold = _step['filling_threshold'] # saturation to add a node as filled node

        self._message_file.write("Termination parameters asserted successfully.\n")
    
    def _define_BCs(self, _inlets, _outlets, _edges):
        '''
        define source functions, boundary conditions and initial conditions
        '''

        # Define source function
        self._body_force = fe.Constant(0) # body force
        self._wall_condition = fe.Constant(0) # pressure difference perpendicular to walls

        # Define inlet and outlet
        self._p_inlet_exp = fe.Constant(_inlets['P_inlet'])
        self._p_outlet_exp = fe.Constant(_outlets['P_outlet'])

        self._vertices_inlet = _edges['Inlet'] + _edges['wall1']
        self._vertices_outlet = _edges['Outlet']
        self._vertices_Wall = _edges['wall2']

        for node in self._vertices_Wall:
            ver=fe.Vertex(self._mesh,node)
            for edge in fe.edges(ver):
                if edge.index() in self._BoundaryEdges:
                    self._boundaries[edge.index()]=3

        for node in self._vertices_inlet:
            ver=fe.Vertex(self._mesh,node)
            for edge in fe.edges(ver):
                if edge.index() in self._BoundaryEdges:
                    self._boundaries[edge.index()]=1
                        
        for node in self._vertices_outlet:
            ver=fe.Vertex(self._mesh,node)
            for edge in fe.edges(ver):
                if edge.index() in self._BoundaryEdges:
                    self._boundaries[edge.index()]=4

        # Set the saturation at the inlet equal to one
        for i in self._vertices_inlet:
            self._saturation[i] = 1.0
            self._FFvsTime[i] = 0.0

        self._message_file.write("IC BC Initialized. \n")
    ################## INITIALIZE DOMAIN AND TIME-STEP ##################################

    def solve(self):

        mesh = self._mesh
        coords = self._coords
        num_nodes = self._num_nodes
        dt = self._dt
        t = self._t
        TEND = self._TEND
        cell_voll = self._cell_voll
        numerator = self._numerator

        domains = self._domains
        boundaries = self._boundaries
        vertices = self._vertices
        p_inlet_exp = self._p_inlet_exp
        p_outlet_exp = self._p_outlet_exp
        ZZ = self._ZZ
        XX = self._XX
        QQ = self._QQ
        p = self._pre_test_function
        q = self._pre_trial_function
        S = self._saturation
        delta_S = self._delta_saturation
        V = self._vel
        FFvsTime = self._FFvsTime
        
        k_exp = self._k_exp[0]
        mu_exp = self._mu_exp
        h = self._h[0]
        phi = self._phi[0]
        g = self._body_force
        w = self._wall_condition

        vertices_inlet = self._vertices_inlet
        vertices_outlet = self._vertices_outlet
        vertices_Wall = self._vertices_Wall

        BoundaryEdges = self._BoundaryEdges
        BoundaryNodes = self._BoundaryNodes
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

        self._message_file.write("Domains constructed. \n")

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
        self._resultsfile.write(ph, t)
        self._resultsfile.write(uh, t)
        self._resultsfile.write(sh, t)

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

        dt = self._t_scaling*dt

        ################## SOLVING IN TIME ##################################
        while (t < fe.DOLFIN_EPS + self._TEND):

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

            for i in range(num_nodes):
                if delta_S[i] != 0.0:
                    delta_S[i] = (delta_S[i])*dt_new/dt
                    S[i] = S[i] + delta_S[i]

            t += dt_new

            # Check if the saturation is changed more than a threshhold 
            if np.amax(delta_S) < self._min_saturation_change:
                self._termination_para += 1
            else:
                self._termination_para = 0

            # Check if the outlet is filled
            self._Outlet_filled = True
            for i in vertices_outlet:
                if S[i] < self._Saturation_threshold:
                    self._Outlet_filled = False

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
                if S[i] > self._Saturation_threshold:
                    available_nodes.add(i)
                if S[i] < self._Saturation_threshold:
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
                self._message_file.write('All CVs are filled! \n')
                for i in range(len(FFvsTime)):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                self._flowfrontfile << ffvstimeh
                break
            elif numerator == self._max_nofiteration:
                self._message_file.write('Maximum iteration number ' + str(self._max_nofiteration) + ' is reached! \n')
                for i in range(len(FFvsTime)):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                self._flowfrontfile << ffvstimeh
                break
            elif self._termination_para > self._Number_consecutive_steps:
                self._message_file.write('Saturation halted for ' + str(self._termination_para) + ' iterations! \n')
                for i in range(len(FFvsTime)):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                self._flowfrontfile << ffvstimeh
                break
            elif self._Outlet_filled == True and True == False:
                self._message_file.write('All outlet nodes are filled! \n')
                for i in range(len(FFvsTime)):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                self._flowfrontfile << ffvstimeh
                break

            facet_on_flow_front = set()

            # Sub domain for walls
        #        wall.mark(boundaries, 3)
            for node in vertices_Wall:
                ver=fe.Vertex(mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in BoundaryEdges:
                        boundaries[edge.index()]=3

            for i in available_cells:
                for e in fe.facets(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
                    if e.entities(0)[0] in nodes_on_flow_front and e.entities(0)[1] in nodes_on_flow_front:
                        facet_on_flow_front.add(e.global_index())
                        boundaries[e] = 2

            for node in vertices_inlet:
                ver=fe.Vertex(mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in BoundaryEdges:
                        boundaries[edge.index()]=1
                            
            for node in vertices_outlet:
                ver=fe.Vertex(mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in BoundaryEdges:
                        boundaries[edge.index()]=4

        #   Check if the domain is change to solve for pressure
            if available_cells_old != available_cells:
                numerator += 1
                self._message_file.write('\nSOLUTION OF THE LINEAR PROBLEM')
                self._message_file.write('\nStep: ' + str(numerator) + ', time:' + str(t) + '\n')

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
            if t > self._current_output_step:
        #        file_results.write(ph, t)
        #        file_results.write(uh, t)
                self._resultsfile.write(sh, t)

                self._current_output_step = self._output_steps + t

                self._domainfile << (domains, t)
                self._boundaryfile << (boundaries, t)