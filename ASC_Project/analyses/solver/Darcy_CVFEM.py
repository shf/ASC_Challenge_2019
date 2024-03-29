# 3D mesh compatible
# the K in 3D need to be adjusted
# Test for flow flux input

from __future__ import absolute_import, unicode_literals

import copy
import logging
import os
import sys
import time
from celery import states

import fenics as fe
import numpy as np

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
        _walls = input['BCs']['walls']
        _hp = input['hp']
#        _Loads = input['loads']
        _step = input['step']
        
        self._logging(_data_handling)
        self._create_output_files(_data_handling)
        self._mesh_initialization(_data_handling)
        self._define_function_space(self._mesh)
        self._define_resin(_resin)
        self._define_sections(_sections)
        self._define_step(_step)
        self._define_BCs(_inlets, _outlets, _walls)
        self._define_initial_conditions()
        if _hp['hp_activated']:
            self._define_openmedium(_hp, _data_handling)
#        self._define_loads(_Loads)
#        self.SolverConfig(_steps, _output)
        return None

    def _logging(self, _data_handling):
        directory_r = _data_handling['folder_address'] + "/results/"
        directory_h = _data_handling['folder_address'] + "/hidden_files/"
        if not os.path.exists(directory_r):
            os.makedirs(directory_r)
        if not os.path.exists(directory_h):
            os.makedirs(directory_h)
        logging.basicConfig(level=logging.DEBUG, filename=directory_h + "/debug.log" , filemode="a+",
            format="%(asctime)-15s %(levelname)-8s %(message)s")
        logging.info("The analysis has been submitted") 

        self._message_file = open(directory_h + "analysis.msg", "w")

    def _create_output_files(self, _data_handling):
        '''
        Create output files to store the analysis results
        '''
        # Files for saving the solution
        self._resultsfile = fe.XDMFFile(_data_handling['folder_address'] + "/results/fillingmedium.xdmf")
        self._resultsfile.parameters["flush_output"] = True
        self._resultsfile.parameters["functions_share_mesh"] = True
        self._resultsfile.parameters["rewrite_function_mesh"] = False

        self._domainfile = fe.File(_data_handling['folder_address'] + "/results/domains.pvd")
        self._boundaryfile = fe.File(_data_handling['folder_address'] + "/results/boundaries.pvd")
        self._materialfile = fe.File(_data_handling['folder_address'] + "/results/materials.pvd")
        self._flowfrontfile = fe.File(_data_handling['folder_address'] + "/results/flowfrontvstime.pvd")
        self._highpressurefile = fe.File(_data_handling['folder_address'] + "/results/highpressure.pvd")
        self._normalsfile = fe.File(_data_handling['folder_address'] + "/hidden_files/cellnormals.pvd")

        self._message_file.write("File handlers created Successfully.\n")

    def _define_resin(self, _resin):

        self._mu_exp = fe.Constant(_resin['viscosity'])
        self._message_file.write("Resin material (viscosity = "+  str(_resin['viscosity']) + ") created successfully. \n")

    def _define_sections(self, _sections):

        self._materials = fe.MeshFunction('size_t', self._mesh, self._mesh.topology().dim())
        self._materials.set_all(1) # correct this

        self._k = {}
        self._h = np.zeros(self._num_nodes)
        self._phi = np.zeros(self._num_nodes)
        self._k_global = {}
        self._message_file.write("Creating Sections ... \n")

        for i in _sections:
            section_id = _sections[i]['marker']
            self._k[section_id] = fe.as_matrix([[_sections[i]['K11'], _sections[i]['K12']], 
            [_sections[i]['K12'], _sections[i]['K22']]])
            self._message_file.write("Section name: " + i + "\n")
            self._message_file.write("Section number: " + str(section_id) + "\n")
            self._message_file.write("Section permeability: " + str(self._k[section_id]) + "\n")
            self._message_file.write("Section thickness: " + str(_sections[i]['thickness']) + "\n")
            self._message_file.write("Section volume fraction: " + str(_sections[i]['volume_fraction']) + "\n")

            for face in _sections[i]['faces']:
                cell=fe.Cell(self._mesh,face)
                for node in cell.entities(0):
                    self._h[node] = _sections[i]['thickness']
                    self._phi[node] = 1.0 - _sections[i]['volume_fraction']
                self._materials[face] = _sections[i]['marker'] 
        if self._dim == 2:
            for i in range(self._num_cells):
                self._k_global[i] = np.array([self._k[self._materials[i]][0][0], self._k[self._materials[i]][0][1]], 
                                            [self._k[self._materials[i]][1][0], self._k[self._materials[i]][1][1]])
        elif self._dim == 3:
            for i in range(self._num_cells):
                self._k_global[i] = np.zeros((3, 3))
                for cell in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim(), i)):
                    normal_on_cell = np.array([cell.cell_normal().x(), cell.cell_normal().y(), cell.cell_normal().z()])
                    z_axis = np.array([0, 0, 1])
                    theta = np.arccos(np.clip(np.dot(normal_on_cell, z_axis), -1.0, 1.0))
                    if normal_on_cell.all() == z_axis.all():
                        n = z_axis
                    else:
                        n = np.cross(normal_on_cell, z_axis)/np.linalg.norm(np.cross(normal_on_cell, z_axis))
                    # Using http://scipp.ucsc.edu/~haber/ph216/rotation_12.pdf

                    k_local = np.array([[self._k[self._materials[i]][0][0], self._k[self._materials[i]][0][1], 0.0], 
                                        [self._k[self._materials[i]][1][0], self._k[self._materials[i]][1][1], 0.0], 
                                        [0.0, 0.0, 0.0]])

                    T = np.array([[np.cos(theta)+n[0]*n[0]*(1.0 - np.cos(theta)), n[0]*n[1]*(1.0 - np.cos(theta)) - n[2]*np.sin(theta), n[0]*n[2]*(1.0 - np.cos(theta)) + n[1]*np.sin(theta)], 
                                [n[0]*n[1]*(1.0 - np.cos(theta)) + n[2]*np.sin(theta), np.cos(theta)+n[1]*n[1]*(1.0 - np.cos(theta)), n[1]*n[2]*(1.0 - np.cos(theta)) - n[0]*np.sin(theta)],  
                                [n[0]*n[2]*(1.0 - np.cos(theta)) - n[1]*np.sin(theta), n[1]*n[2]*(1.0 - np.cos(theta)) + n[0]*np.sin(theta), np.cos(theta)+n[2]*n[2]*(1.0 - np.cos(theta))]])
                    
                self._k_global[i] = np.matmul(np.matmul(T,k_local),np.transpose(T))
        else:
            self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
            progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })

                
        class Permeability(fe.UserExpression):
            def __init__(self, materials, k, dim, **kwargs):
                self.__materials = materials
                self.__k_global = k
                self.__dim = dim
                super().__init__(**kwargs)
        
            def eval_cell(self, values, x, ufc_cell):
                if self.__dim == 2:
                    values[0] = self.__k_global[ufc_cell.index][0][0]
                    values[1] = self.__k_global[ufc_cell.index][0][1]
                    values[2] = self.__k_global[ufc_cell.index][1][0]
                    values[3] = self.__k_global[ufc_cell.index][1][1]
                elif self.__dim == 3:
                    values[0] = self.__k_global[ufc_cell.index][0][0]
                    values[1] = self.__k_global[ufc_cell.index][0][1]
                    values[2] = self.__k_global[ufc_cell.index][0][2]
                    values[3] = self.__k_global[ufc_cell.index][1][0]
                    values[4] = self.__k_global[ufc_cell.index][1][1]
                    values[5] = self.__k_global[ufc_cell.index][1][2]
                    values[6] = self.__k_global[ufc_cell.index][2][0]
                    values[7] = self.__k_global[ufc_cell.index][2][1]
                    values[8] = self.__k_global[ufc_cell.index][2][2]
                else:
                    self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
                    progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
                    return 0
            
            def value_shape(self):
                if self.__dim == 2:
                    return (2, 2)
                elif self.__dim == 3:
                    return (3, 3)
                else:
                    self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
                    progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
                    return 0

        self._k_exp = Permeability(self._materials, self._k_global, self._dim, degree=1)

        class Normalls(fe.UserExpression):
            def __init__(self, mesh, dim, **kwargs):
                self.__dim = dim
                self.__mesh = mesh
                super().__init__(**kwargs)

            def eval_cell(self, values, x, ufc_cell):
                if self.__dim == 3:
                    for cell in fe.cells(fe.MeshEntity(self.__mesh, self.__mesh.topology().dim(), ufc_cell.index)):
                        values[0] = cell.cell_normal().x()
                        values[1] = cell.cell_normal().y()
                        values[2] = cell.cell_normal().z()
            def value_shape(self):
                if self.__dim == 3:
                    return (3,)

        self._normal_exp = Normalls(self._mesh, self._dim, degree=2)

        nh = fe.project(self._normal_exp, self._XX)
        nh.rename("Normals", "")

        self._normalsfile << nh 

        v2d = fe.vertex_to_dof_map(self._QQ)
        self._h_exp = fe.Function(self._QQ)
        self._h_exp.rename("Thickness", "")
        for i in range(len(self._h)):
            self._h_exp.vector()[v2d[i]] = self._h[i]

        self._phi_exp = fe.Function(self._QQ)
        self._phi_exp.rename("Thickness", "")
        for i in range(len(self._phi)):
            self._phi_exp.vector()[v2d[i]] = self._phi[i]

        self._message_file.write("Section material created successfully. \n")

    def _mesh_initialization(self, _data_handling):

        '''
        Initializing the mesh and setting the number of nodes and cells and
        cell volumes
        '''
        # Create mesh
        self._message_file.write("\nMESH PRE-PROCESSING \n")
        self._message_file.write("Creating mesh in FEniCS for analysis" + str(_data_handling['analysis_id']) + "... \n")

        self._mesh = fe.Mesh(_data_handling['folder_address'] + "/mesh.xml")
        self._mesh.rename("Current_mesh", "")

 
        self._coords = self._mesh.coordinates() # coordination of vertices
        self._dim = np.shape(self._coords)[1]
        self._num_nodes = self._mesh.num_vertices() # number of vertices
        self._num_cells = self._mesh.num_cells() # number of cells

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
        self._highpressure = np.zeros(self._num_nodes) # Saturation vector
        self._delta_saturation = np.zeros(self._num_nodes) # growth of saturation in one step
        if self._dim == 2:
            self._vel = np.zeros((self._num_nodes, 2)) # Velocity Vector
        elif self._dim == 3:
            self._vel = np.zeros((self._num_nodes, 3)) # Velocity Vector
        else:
            self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
            progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
            return 0
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

        self._termination_type = _step['termination_type']
        self._termination_para = 0
        self._TEND = _step['termination_time'] # end time - for halting analysis
        self._max_nofiteration = _step['maximum_itrations'] # maximum number of iterations for pressure
        self._Number_consecutive_steps = _step['maximum_consequtive_steps'] # number of consecutive steps without change in S
        self._min_saturation_change = _step['minimum_change_of_saturation'] # minimum saturation change for termination
        self._outlet_filled = False

        self._t_scaling = _step['time_scaling_parameter'] # scaling of first time-step
        self._Saturation_threshold = _step['filling_threshold'] # saturation to add a node as filled node

        self._message_file.write("Termination parameters asserted successfully.\n")
    
    def _define_BCs(self, _inlets, _outlets, _walls):
        '''
        define source functions, boundary conditions and initial conditions
        '''
        self._inlets = _inlets
        self._outlets = _outlets
        self._walls = _walls

        # Define inlet and outlet
        self._vertices_inlet = []
        self._vertices_outlet = []
        self._pressure_inlet_dicts = []
        self._flux_inlet_info = {}
        self._pressure_outlet_dicts = []

        for i in self._inlets:
            self._vertices_inlet += self._inlets[i]['nodes'][:]

        for i in self._outlets:
            self._vertices_outlet += self._outlets[i]['nodes'][:]

        for i in self._walls:
            for node in self._walls[i]['nodes']:
                ver=fe.Vertex(self._mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in self._BoundaryEdges:
                        self._boundaries[edge.index()]=self._walls[i]['marker']

        for i in self._inlets:
            for node in self._inlets[i]['nodes']:
                ver=fe.Vertex(self._mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in self._BoundaryEdges:
                        self._boundaries[edge.index()]=self._inlets[i]['marker']
            if self._inlets[i]['condition'] == 'Pressure':
                self._pressure_inlet_dicts.append(i)
            else:
                self._flux_inlet_info[i] = {}
        
        self._min_outlet_pressure = 0.0
        for i in self._outlets:
            for node in self._outlets[i]['nodes']:
                ver=fe.Vertex(self._mesh,node)
                for edge in fe.edges(ver):
                    if edge.index() in self._BoundaryEdges:
                        self._boundaries[edge.index()]=self._outlets[i]['marker']
            if self._outlets[i]['condition'] == 'Pressure':
                self._pressure_outlet_dicts.append(i)
                self._min_outlet_pressure = min(self._min_outlet_pressure, self._outlets[i]['value'])
        
        self._vel_inlet = np.zeros(self._num_nodes)

        for i in self._flux_inlet_info.keys():
            for node in self._inlets[i]['nodes']:
                ver = fe.Vertex(self._mesh,node)
                width = 0.0
                for edge in fe.edges(ver):
                    entity=edge.entities(0)
                    if all(item in self._inlets[i]['nodes'] for item in entity):
                        width = width + edge.length()/2
                area = width*self._h[node]
                self._vel_inlet[node] = self._inlets[i]['value']/area            
        
        v2d = fe.vertex_to_dof_map(self._QQ)
        self._vel_exp = fe.Function(self._QQ)
        self._vel_exp.rename("VelocityInlet", "")
        for i in range(len(self._vel_inlet)):
            self._vel_exp.vector()[v2d[i]] = self._vel_inlet[i]

    def _define_initial_conditions(self):
        '''
        define initial conditions and source terms
        '''
        # Set the saturation at the inlet equal to one
        # and find the maximum distance of nodes to inlet

        self._max_distant = 0.0

        for v_i in self._vertices_inlet:
            coord_i = self._coords[v_i]
            self._saturation[v_i] = 0.0
            self._FFvsTime[v_i] = 0.0
            for v_j in range(self._num_nodes):
                coord_j = self._coords[v_j]
                distance = np.linalg.norm(coord_i - coord_j)
                self._max_distant = max(self._max_distant, distance)

        # Define source function
        self._body_force = fe.Constant(0.0) # body force
        self._wall_condition = fe.Constant(0.0) # pressure difference perpendicular to walls

        self._cell_voll = np.zeros(self._num_nodes) # Volume of CV cells

        for i in range(len(self._cell_voll)):
            for shared_cell in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim()-2, i)):
                self._cell_voll[i] = self._cell_voll[i] + (shared_cell.volume()/3.0)*self._h[i]*self._phi[i]

        self._message_file.write("Initial conditions applied. \n")
    
    def _define_openmedium(self, _hp, _data_handling):
        '''
        Initializing the mesh and setting the number of nodes and cells and
        cell volumes
        '''
        self._message_file.write("Creating open medium properties... \n")
        
        # Files for saving the solution of open medium
        self._flowfrontfile_medium = fe.File(_data_handling['folder_address'] + "/results/flowfrontvstime_medium.pvd")

        self._k_medium = _hp['K_medium']
        self._h_medium = _hp['h_medium']
        self._phi_medium = _hp['phi_medium']

        self._k_medium_exp = fe.Constant(self._k_medium)
        self._h_medium_exp = fe.Constant(self._h_medium)
        self._phi_medium_exp = fe.Constant(self._phi_medium)
        
        self._saturation_medium = np.zeros(self._num_nodes) # Saturation vector
        self._delta_saturation_medium = np.zeros(self._num_nodes) # growth of saturation in one step

        if self._dim == 2:
            self._vel_medium = np.zeros((self._num_nodes, 2)) # Velocity Vector
        elif self._dim == 3:
            self._vel_medium = np.zeros((self._num_nodes, 3)) # Velocity Vector
        else:
            self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
            progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
            return 0
        self._FFvsTime_medium = np.zeros(self._num_nodes)

        self._cell_voll_medium = np.zeros(self._num_nodes)
        
        for i in range(len(self._cell_voll_medium)):
            for shared_cell in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim()-2, i)):
                self._cell_voll_medium[i] = self._cell_voll_medium[i] + (shared_cell.volume()/3.0)
        self._cell_voll_medium = self._cell_voll_medium*self._h_medium*self._phi_medium

    ################## INITIALIZE DOMAIN AND TIME-STEP ##################################
    def _find_dtime(self, available_cells, vertices_inlet, V, h, S, cell_voll):
        dt = self._TEND
        for i in available_cells:
            for c in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim(), i)):
                cell_midpoint = (self._coords[c.entities(0)[0]]+self._coords[c.entities(0)[1]]+self._coords[c.entities(0)[2]])/3.0
                for v_i in c.entities(0):
                    if S[v_i] < 1.0:
                        for v_j in c.entities(0):
                            if v_j in vertices_inlet and v_j != v_i:
                                coord_i = self._coords[v_i]
                                coord_j = self._coords[v_j]
                                edge_midpoint = (coord_i + coord_j)/2.0
                                if self._dim == 2:
                                    norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                                    normal = [-(cell_midpoint[1] - edge_midpoint[1]), (cell_midpoint[0] - edge_midpoint[0])]/norm
                                    distance = np.linalg.norm(coord_i - coord_j)
                                    inward_normal = [(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])]/distance

                                    if np.dot(inward_normal, normal) < 0:
                                        normal = -normal

                                elif self._dim == 3:
                                    norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                                    normal_on_cell = np.cross(cell_midpoint - edge_midpoint, coord_i - coord_j)
                                    normal_on_edge = np.cross(normal_on_cell, cell_midpoint - edge_midpoint)
                                    normal = normal_on_edge / np.linalg.norm(normal_on_edge)
                                    distance =  np.linalg.norm(coord_i - coord_j)
                                    inward_normal = (coord_i - coord_j)/distance
                                
                                    if np.dot(inward_normal, normal) < 0:
                                        normal = -normal
                                else:
                                    self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
                                    progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
                                    return 0

                                vel = (V[v_i] + V[v_j])/2.0
                                flux = np.dot(vel, normal)*norm*h[v_i]
                                dt = min(dt, (1 - S[v_i])*(cell_voll[v_i])/abs(flux))
        return dt

    def _find_fillfactor(self, available_cells, V, dt, h, delta_S, S, cell_voll):
        for i in available_cells:
                for c in fe.cells(fe.MeshEntity(self._mesh, self._mesh.topology().dim(), i)):
                    cell_midpoint = (self._coords[c.entities(0)[0]]+self._coords[c.entities(0)[1]]+self._coords[c.entities(0)[2]])/3.0
                    for v_i in c.entities(0):
                        if S[v_i] < 1.0:
                            for v_j in c.entities(0):
                                if v_j != v_i:
                                    coord_i = self._coords[v_i]
                                    coord_j = self._coords[v_j]
                                    edge_midpoint = (coord_i + coord_j)/2.0
                                    if self._dim == 2:
                                        norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                                        normal = [-(cell_midpoint[1] - edge_midpoint[1]), (cell_midpoint[0] - edge_midpoint[0])]/norm
                                        distance = np.linalg.norm(coord_i - coord_j)
                                        inward_normal = [(coord_i[0] - coord_j[0]), (coord_i[1] - coord_j[1])]/distance

                                        if np.dot(inward_normal, normal) < 0:
                                            normal = -normal

                                    elif self._dim == 3:
                                        norm = np.linalg.norm(cell_midpoint - edge_midpoint)
                                        normal_on_cell = np.cross(cell_midpoint - edge_midpoint, coord_i - coord_j)
                                        normal_on_edge = np.cross(normal_on_cell, cell_midpoint - edge_midpoint)
                                        normal = normal_on_edge / np.linalg.norm(normal_on_edge)
                                        distance =  np.linalg.norm(coord_i - coord_j)
                                        inward_normal = (coord_i - coord_j)/distance
                                    
                                        if np.dot(inward_normal, normal) < 0:
                                            normal = -normal
                                    else:
                                        self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
                                        progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })

                                    vel = (V[v_i] + V[v_j])/2.0
                                    flux = np.dot(vel, normal)*norm*h[v_i]
                                    delta_S[v_i] = delta_S[v_i] + dt*(abs(flux))/(cell_voll[v_i])
        return delta_S

    def solve_rtm(self, progress):

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
        materials = self._materials
        vertices = self._vertices
        ZZ = self._ZZ
        XX = self._XX
        QQ = self._QQ
        p = self._pre_test_function
        q = self._pre_trial_function
        S = self._saturation
        HP = self._highpressure
        delta_S = self._delta_saturation
        V = self._vel
        FFvsTime = self._FFvsTime
        k_exp = self._k_exp
      
        mu_exp = self._mu_exp
        phi_exp = self._phi_exp
        h_exp = self._h_exp
        h = self._h
        g = self._body_force
        w = self._wall_condition

        vertices_inlet = self._vertices_inlet
        vertices_outlet = self._vertices_outlet

        BoundaryEdges = self._BoundaryEdges
        BoundaryNodes = self._BoundaryNodes

        # Book-keeping nodes and facets
        available_nodes = set() # nodes in the domain
        available_cells = set() # cells of the domain
        nodes_on_flow_front = set() # nodes on the flow front
        facet_on_flow_front = set() # facets on the flow front

        # populating nodes on the domain
        for i in self._vertices_inlet:
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
                        vertices[vertice] = 99

        for i in available_cells:
            for e in fe.facets(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
                    if e.entities(0)[0] in nodes_on_flow_front and e.entities(0)[1] in nodes_on_flow_front:
                        facet_on_flow_front.add(e.global_index())
                        if boundaries[e] == 0:
                            boundaries[e] = 99

        # boundary conditions for pressure
        bcs = []
        for i in self._pressure_inlet_dicts:
            bcs.append(fe.DirichletBC(ZZ, self._inlets[i]['value'], boundaries, self._inlets[i]['marker']))

        for i in self._pressure_outlet_dicts:
            bcs.append(fe.DirichletBC(ZZ, self._outlets[i]['value'], boundaries, self._outlets[i]['marker']))

        # boundary condition for flow-front
        bc_flowfront = [fe.DirichletBC(ZZ, self._min_outlet_pressure, boundaries, 99)]

        # a) set BC and Domain in each step
        # Domain
        dx_domain = fe.Measure('dx')(subdomain_data=domains)
        ds_wall = fe.Measure("ds")(subdomain_data=boundaries)

        self._message_file.write("Domains constructed. \n")

        # b) variational problem and computing pressure
        normal_terms = []
        for i in self._flux_inlet_info.keys():
            normal_terms.append(self._vel_exp*q*ds_wall(self._inlets[i]['marker']))
        
        for i in self._walls:
            normal_terms.append(w*q*ds_wall(self._walls[i]['marker']))

        a = fe.inner(k_exp/mu_exp*fe.grad(p), fe.grad(q))*dx_domain(1) + p*q*dx_domain(0)
        L = g*q*dx_domain(1) + sum(term for term in normal_terms) + g*q*dx_domain(0)
        ph = fe.Function(ZZ)
        fe.solve(a == L, ph, bcs + bc_flowfront)
        ph.rename("Pressure", "")

        # c) postprocess velocity
        uh = fe.project(-k_exp/mu_exp*fe.grad(ph), XX)
        d2v = fe.dof_to_vertex_map(XX)

        if self._dim == 2:
            for i in range(len(V)):
                V[int(d2v[2*i]/2), 0] = uh.vector()[2*i]
                V[int(d2v[2*i]/2), 1] = uh.vector()[2*i+1]
        elif self._dim == 3:
            for i in range(len(V)):
                V[int(d2v[3*i]/3), 0] = uh.vector()[3*i]
                V[int(d2v[3*i]/3), 1] = uh.vector()[3*i+1]
                V[int(d2v[3*i]/3), 2] = uh.vector()[3*i+2]
        else:
            self._message_file.write('\nInternal Error: Mesh dimension is not accepted! \n')
            progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })
        uh.rename("velocity", "")

        # d) assign saturation
        sh = fe.Function(QQ)
        ffvstimeh = fe.Function(QQ)
        sh.rename("Saturation", "")
        hpcontour = fe.Function(ZZ)
        hpcontour.rename("HighPressureContour", "")
        ffvstimeh.rename("FlowfrontvsTime", "")
        v2d = fe.vertex_to_dof_map(QQ)
        v2d_zz = ZZ.dofmap().entity_dofs(self._mesh, 0)
        for i in range(num_nodes):
            sh.vector()[v2d[i]] = S[i]
            HP[i] = ph.vector()[v2d_zz[i]]

        # e) plot solution and write output file
        self._resultsfile.write(ph, t)
        self._resultsfile.write(uh, t)
        self._resultsfile.write(sh, t)

        dt = TEND

        dt = self._find_dtime(available_cells, vertices_inlet, V, h, S, cell_voll)

        dt = self._t_scaling*dt
        ################## SOLVING IN TIME ##################################
        while (t < fe.DOLFIN_EPS + self._TEND):

            delta_S.fill(0)

            # Find fill factor for predicted time-step
            delta_S = self._find_fillfactor(available_cells, V, dt, h, delta_S, S, cell_voll)

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
                        dt_new = min(dt_new, (dt*(1.0 - S[i])/(delta_S[i])))
            else:
                self._message_file.write('\nInternal Error: Maximum saturation is less than 1.0! \n')
                progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })

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

            # Print saturation for the user
            for i in available_cells:
                for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
                    for v_i in c.entities(0):
                        sh.vector()[v2d[v_i]] = S[v_i]

            # finding available cells and time-step for next step
            nodes_on_flow_front = set()

            boundaries.set_all(0)
            vertices.set_all(0)

            available_nodes_old = copy.deepcopy(available_nodes)
            available_cells_old = copy.deepcopy(available_cells)

            # add nodes with S > thershhold to available nodes
            for i in set(range(num_nodes)) - available_nodes:
                if S[i] > self._Saturation_threshold:
                    available_nodes.add(i)
                    
            # find available domains
            for i in available_nodes - available_nodes_old:
                for c in fe.cells(fe.MeshEntity(mesh, mesh.topology().dim()-2, i)):
                    available_cells.add(c.global_index())
                    domains[c] = 1

            # find flowfront(nodes not in available nodes)
            for c in available_cells:
                for vertice in fe.vertices(fe.MeshEntity(mesh, mesh.topology().dim(), c)):
                    if vertice.index() not in available_nodes:
                        nodes_on_flow_front.add(vertice.global_index())
                        vertices[vertice] = 99

            # adding time to nodes on flow front
            if available_nodes_old != available_nodes:
                for i in available_nodes - available_nodes_old:
                    FFvsTime[i] = t

            # termination cases
            if len(available_nodes) == num_nodes and self._termination_type == 'Fill everywhere':
                self._message_file.write('\nAll CVs are filled! \n')
                progress.update_state(state=states.SUCCESS,  meta={'message':'All CVs are filled! <br>' })
                for i in range(num_nodes):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                    hpcontour.vector()[v2d_zz[i]] = HP[i]
                self._flowfrontfile << ffvstimeh
                self._highpressurefile << hpcontour
                time.sleep(3)
                return 0
            elif numerator == self._max_nofiteration:
                for i in set(range(self._num_nodes)) - available_nodes:
                    FFvsTime[i] = t
                self._message_file.write('\nMaximum iteration number ' + str(self._max_nofiteration) + ' is reached! \n')
                progress.update_state(state=states.SUCCESS,  meta={'message':'Maximum iteration number ' + str(self._max_nofiteration) + ' is reached! <br>' })
                for i in range(num_nodes):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                    hpcontour.vector()[v2d_zz[i]] = HP[i]
                self._flowfrontfile << ffvstimeh
                self._highpressurefile << hpcontour
                time.sleep(3)
                return 0
            elif t > TEND:
                for i in set(range(self._num_nodes)) - available_nodes:
                    FFvsTime[i] = t
                message = '\nMaximum filling time is reached! \n'
                self._message_file.write(message)
                progress.update_state(state=states.SUCCESS,  meta={'message':'Maximum filling time is reached! <br>' })
                for i in range(num_nodes):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                    hpcontour.vector()[v2d_zz[i]] = HP[i]
                self._flowfrontfile << ffvstimeh
                self._highpressurefile << hpcontour
                time.sleep(3)
                return 0
            elif self._termination_para > self._Number_consecutive_steps:
                for i in set(range(self._num_nodes)) - available_nodes:
                    FFvsTime[i] = t
                self._message_file.write('\nSaturation halted for ' + str(self._termination_para) + ' iterations! \n')
                progress.update_state(state="TERMINATE",  meta={'message':'Saturation halted for ' + str(self._termination_para) + ' iterations! <br>' })
                for i in range(num_nodes):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                    hpcontour.vector()[v2d_zz[i]] = HP[i]
                self._flowfrontfile << ffvstimeh
                self._highpressurefile << hpcontour
                time.sleep(3)
                return 0
            elif self._Outlet_filled == True and self._termination_type == 'Fill the outlet':
                for i in set(range(self._num_nodes)) - available_nodes:
                    FFvsTime[i] = t
                self._message_file.write('\nAll outlet nodes are filled! \n')
                progress.update_state(state=states.SUCCESS,  meta={'message':'All outlet nodes are filled! <br>' })
                for i in range(num_nodes):
                    ffvstimeh.vector()[v2d[i]] = FFvsTime[i]
                    hpcontour.vector()[v2d_zz[i]] = HP[i]
                self._flowfrontfile << ffvstimeh
                self._highpressurefile << hpcontour
                time.sleep(3)
                return 0

            facet_on_flow_front = set()

            # renew boundary conditions
            self._define_BCs(self._inlets, self._outlets, self._walls)
            boundaries = self._boundaries

            # renew boundaries
            for i in available_cells:
                for e in fe.facets(fe.MeshEntity(mesh, mesh.topology().dim(), i)):
                    if e.entities(0)[0] in nodes_on_flow_front and e.entities(0)[1] in nodes_on_flow_front:
                        facet_on_flow_front.add(e.global_index())
                        if boundaries[e] == 0:
                            boundaries[e] = 99

        #   Check if the domain is change to solve for pressure
            if available_cells_old != available_cells:
                numerator += 1

                progress.update_state(state="PROGRESS",  meta={'iteration': numerator, 'fill_time': round(t,4), 'percent':(len(available_nodes)/self._num_nodes), 'numOfFilled':len(available_nodes), 'numofCells':self._num_nodes})

                self._message_file.write('\nSOLUTION OF THE LINEAR PROBLEM')
                self._message_file.write('\nStep: ' + str(numerator) + ', time:' + str(t) + '\n')

                # boundary condition for gate
                bcs = []
                for i in self._pressure_inlet_dicts:
                    bcs.append(fe.DirichletBC(ZZ, self._inlets[i]['value'], boundaries, self._inlets[i]['marker']))

                for i in self._pressure_outlet_dicts:
                    bcs.append(fe.DirichletBC(ZZ, self._outlets[i]['value'], boundaries, self._outlets[i]['marker']))

                # boundary condition for flow front
                bc_flowfront = [fe.DirichletBC(ZZ, self._min_outlet_pressure, boundaries, 99)]

                # set BC and Domain in each step
                # Domain
                dx_domain = fe.Measure('dx')(subdomain_data=domains)
                ds_wall = fe.Measure("ds")(subdomain_data=boundaries)

                # variational problem and computing pressure
                normal_terms = []
                for i in self._flux_inlet_info.keys():
                    normal_terms.append(self._vel_exp*q*ds_wall(self._inlets[i]['marker']))
                
                for i in self._walls:
                    normal_terms.append(w*q*ds_wall(self._walls[i]['marker']))
                
                a = fe.inner(k_exp/mu_exp*fe.grad(p), fe.grad(q))*dx_domain(1) + p*q*dx_domain(0)
                L = g*q*dx_domain(1) + sum(term for term in normal_terms) + g*q*dx_domain(0)

                ph = fe.Function(ZZ)

                fe.solve(a == L, ph, bcs + bc_flowfront)
                ph.rename("Pressure", "")

                for i in range(num_nodes):
                    HP[i] = max(ph.vector()[v2d_zz[i]], HP[i])

                # postprocess velocity
                uh = fe.project(-k_exp/mu_exp*fe.grad(ph), XX)
                d2v = fe.dof_to_vertex_map(XX)
                if self._dim == 2:
                    for i in range(len(V)):
                        V[int(d2v[2*i]/2), 0] = uh.vector()[2*i]
                        V[int(d2v[2*i]/2), 1] = uh.vector()[2*i+1]
                elif self._dim == 3:
                    for i in range(len(V)):
                        V[int(d2v[3*i]/3), 0] = uh.vector()[3*i]
                        V[int(d2v[3*i]/3), 1] = uh.vector()[3*i+1]
                        V[int(d2v[3*i]/3), 2] = uh.vector()[3*i+2]
                uh.rename("velocity", "")

            # plot solution and write output file
            if t > self._current_output_step:
                self._resultsfile.write(ph, t)
                self._resultsfile.write(uh, t)
                self._resultsfile.write(sh, t)

                self._current_output_step = self._output_steps + t

                self._domainfile << (domains, t)
                self._boundaryfile << (boundaries, t)
                self._materialfile << (materials, t)

### SOLVE HP RTM
    def solve_hprtm(self, progress):
        self._message_file.write('\nThis capability has not been implemented yet! \n')
        progress.update_state(state=states.FAILURE,  meta={'message': 'Internal Error! Check message file for more information!' })

        