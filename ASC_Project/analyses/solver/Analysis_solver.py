from .Darcy_CVFEM import Darcy_CVFEM
from ..models import (BC, Analysis, Connectivity, Mesh, Nodes, Preform, Resin,
                     Section, Step, Results)
                
import numpy as np

def solve_darcy(_analysis):
    '''
    This function creates an instance for the Darcy_FEM solver class
    based on the database information 
    '''

    resin = _analysis.resin
    viscosity = resin.viscosity

    KXX = {}
    KXY = {}
    KYY = {}
    H = {}
    phi = {}
    sections = _analysis.section.all()
    for section in sections:
        H[section.name] = 0.0
        KXX[section.name] = 0.0
        KXY[section.name] = 0.0
        KYY[section.name] = 0.0
        phi[section.name] = 0.0
        preforms = section.preform
        radian_rot = np.deg2rad(section.rotate)
        T = np.array([[np.cos(radian_rot), np.sin(radian_rot)], [-np.sin(radian_rot), np.cos(radian_rot)]])
#        for preform in preforms:
        preform = preforms
        H[section.name] = H[section.name] + preform.thickness
        phi[section.name] = phi[section.name] + preform.phi*preform.thickness
        k = T * np.array([[preform.K11, preform.K12], [preform.K12, preform.K12]])
        KXX[section.name] = KXX[section.name] + preform.thickness * k[0][0]
        KXY[section.name] = KXY[section.name] + preform.thickness * k[0][1]
        KYY[section.name] = KYY[section.name] + preform.thickness * k[1][1]
        KXX[section.name] = KXX[section.name]/H[section.name]
        KXY[section.name] = KXY[section.name]/H[section.name]
        KYY[section.name] = KYY[section.name]/H[section.name]
        phi[section.name] = phi[section.name]/H[section.name]

## rotation is not used

    EdgeList = {}

    for items in Nodes.objects.filter(mesh_id=_analysis.mesh).values():
        if items['EdgeGroup'] not in EdgeList.keys():
            EdgeList[items['EdgeGroup']] = []
        EdgeList[items['EdgeGroup']].append(items['NodeNum'])
    del EdgeList["_None"]

    analysis = {
        'analysis_id':_analysis.id,
        'folder_address':("media/" + str(_analysis.id))
    }

    resin = {
        'viscosity':viscosity
    }
    section_data = {}
    section_id = 0
    for section in sections:
        section_data[section_id]={
            'section_name':section.name,
            'K11':KXX[section.name],
            'K12':KXY[section.name],
            'K22':KYY[section.name],
            'thickness':H[section.name],
            'volume_fraction':phi[section.name]
        }
        section_id = section_id + 1

    step = _analysis.step

    step_data = {
        'termination_time':step.endtime,
        'output_steps':step.outputstep,
        'maximum_itrations':step.maxiterations,
        'maximum_consequtive_steps':step.maxhaltsteps, 
        'minimum_change_of_saturation':step.minchangesaturation,
        'time_scaling_parameter':step.timescaling,
        'filling_threshold':step.fillthreshold,
    }

    BCs = {
        'inlets':{
            'P_inlet':100000
        },
        'outlets':{
            'P_outlet':0
        },
        'edges':{
            'Inlet':EdgeList['Inlet'],
            'Outlet':EdgeList['Outlet'],
            'wall1':EdgeList['wall1'],
            'wall2':EdgeList['wall2'],
        }
    }

    InputData = {
        'analysis': analysis,
        'resin':resin,
        'sections':section_data,
        'step':step_data,
        'BCs':BCs,
#        'ICs':InitialConditions,
#        'loads':Loads,
#        'output':Output
    }

    problem=Darcy_CVFEM(InputData)
    problem.solve() 
