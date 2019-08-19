from .Darcy_CVFEM import Darcy_CVFEM

def solve_darcy(analysis_id, Edges):
    '''
    This function creates an instance for the Darcy_FEM solver class
    based on the database information 
    '''

    analysis = {
        'analysis_id':analysis_id,
        'folder_address':("media/" + str(analysis_id))
    }

    materials = {
        'resin':{
            'viscosity':0.2
        },
        'preform':{
            'K11':1e-10,
            'thickness':0.1,
            'volume_fraction':0.5
        }
    }

    step = {
        'output_steps':0.0,
        'termination_time':1000,
        'maximum_itrations':10000,
        'maximum_consequtive_steps':3, 
        'minimum_change_of_saturation':1e-3,
        'time_scaling_parameter':5.0,
        'filling_threshold':0.98,
    }

    BCs = {
        'inlets':{
            'P_inlet':100000
        },
        'outlets':{
            'P_outlet':0
        },
        'edges':{
            'Inlet':Edges['Inlet'],
            'Outlet':Edges['Outlet'],
            'wall1':Edges['wall1'],
            'wall2':Edges['wall2'],
        }
    }

    InputData = {
        'analysis': analysis,
        'materials':materials,
#        'sections':sections,
        'step':step,
        'BCs':BCs,
#        'ICs':InitialConditions,
#        'loads':Loads,
#        'output':Output
    }

    problem=Darcy_CVFEM(InputData)
    problem.solve() 
