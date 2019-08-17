import plotly.graph_objs as go
import plotly.offline as opy
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaulttags import register
from django.contrib import messages

from .forms import (MeshConfirmationForm, NewAnalysisForm, NewBCForm,
                    NewMeshForm, NewPreformForm, NewResinForm, NewSectionForm,
                    NewStepForm, JobSubmitForm, ResultsForm)
from .models import (BC, Analysis, Connectivity, Mesh, Nodes, Preform, Resin,
                     Section, Step, Results)
from .solver.Importers import MeshImport, Contour


def PlotlyPlot (nodes, table, intensity):
    xn = []
    yn = []
    zn = []
    for line in nodes.values():
        xn.append(line["x"])
        yn.append(line["y"])
        zn.append(line["z"])

    
    ii = []
    jj = []
    kk = []

    for line in table.values():
        ii.append(line["N1"])
        jj.append(line["N2"])
        kk.append(line["N3"])

    # define lines of each element
    x_line = []
    y_line = []
    z_line = []
    for t in range(len(ii)):
        elem = [ii[t], jj[t], kk[t], ii[t]]
        x_line.extend([xn[v] for v in elem]+[None])
        y_line.extend([yn[v] for v in elem]+[None])
        z_line.extend([zn[v] for v in elem]+[None])
    colorbar_title="Field"
    if intensity:
        
        showscale=True
    else:
        showscale=False

    figure = go.Figure(data=[
        go.Mesh3d(
            x=xn,
            y=yn,
            z=zn,
            showscale=showscale,
            
            color='darkturquoise',
            colorscale='RdBu',
            colorbar_title=colorbar_title,
            intensity=intensity,
            i=ii,
            j=jj,
            k=kk,
        ),
        go.Scatter3d(
            x=x_line,
            y=y_line,
            z=z_line,
            mode='lines',
            line=dict(color='rgb(50,50,50)', width=1.5)
        )
    ],
        layout=dict(
            height=600,
            dragmode='pan',
            scene=dict(
                xaxis=dict(
                    visible=False
                ),
                yaxis=dict(
                    visible=False
                ),
                zaxis=dict(
                    visible=False
                ),
                camera=dict(
                    up=dict(x=0, y=0, z=0),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=0, y=0, z=1.5)
                )
            )
    )
    )

    return opy.plot(figure, auto_open=False, output_type='div')

# dictionary for sidebar switching
@register.filter
def get_active(dictionary, key):
    return dictionary.get(key)[0]
@register.filter
def get_show(dictionary, key):
    return dictionary.get(key)[1]

class SideBarPage():
    def __init__(self):
        self._page ={
            'mesh':["<li class=\"nav-item\">","<div id=\"collapse_mesh\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'resin':["<li class=\"nav-item\">","<div id=\"collapse_resin\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'preform':["<li class=\"nav-item\">","<div id=\"collapse_preform\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'section':["<li class=\"nav-item\">","<div id=\"collapse_section\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'step':["<li class=\"nav-item\">","<div id=\"collapse_step\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'bc':["<li class=\"nav-item\">","<div id=\"collapse_bc\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'submit':["<li class=\"nav-item\">","<div id=\"collapse_submit\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'results':["<li class=\"nav-item\">","<div id=\"collapse_submit\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"]
            }
    def DicUpdate(self,page):
        self._page[page]=['<li class=\"nav-item active\">',"<div id=\"collapse_{}\" class=\"collapse show\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">".format(page)]
        return self._page

# variables to pass in all views
class NoObject():
    def __init__(self,_name):
        self._name=_name
    @property
    def name(self):
        return self._name

def PageVariables(Page,form,analysis):
    ViewsVars={'page': Page,
        'form': form,
        'analysis': analysis,
        'preforms': analysis.preform.all(),
        'sections': analysis.section.all(),
        'bc': analysis.bc.all()}
    try:
        ViewsVars['mesh']=analysis.mesh
    except:
        ViewsVars['mesh']=NoObject("Empty")
    try:
        ViewsVars['resin']=analysis.resin
    except:
        ViewsVars['resin']=NoObject("Empty")   
    try:
        ViewsVars['step']=analysis.step
    except:
        ViewsVars['step']=NoObject("Empty")    
    return ViewsVars

# views:
def home(request):
    analysis = Analysis.objects.all()
    if request.method == 'POST':
        form = NewAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.save()

            return redirect('mesh', slug=analysis.name)
    else:
        form = NewAnalysisForm()
    Page = SideBarPage().DicUpdate("")
    return render(request, 'home.html', {'page':Page, 'form': form})


def mesh_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewMeshForm(request.POST, request.FILES)
        if form.is_valid():
            mesh = form.save(commit=False)
            mesh.analysis = analysis
            mesh.save()
            Address = get_object_or_404(Mesh, id=mesh.id)
            
            # mesh name from file name
            mesh.name=str(Address.address).split("/")[1].split(".")[0]

            # save mesh in xml format
            MeshImp = MeshImport("media/"+str(Address.address))
            MeshImp.UNVtoXMLConverter()

            # save mesh data in database
            nodes, ConnectivityTable = MeshImp.MeshData()
            for key, value in nodes.items():
                Nodes.objects.create(NodeNum=int(key), x=float(
                    value[0]), y=float(value[1]), z=float(value[2]), mesh=mesh)
            for key, value in ConnectivityTable.items():
                Connectivity.objects.create(ElmNum=int(key), N1=float(
                    value[0]), N2=float(value[1]), N3=float(value[2]), mesh=mesh)

            edges, faces = MeshImp.MeshGroups()
            mesh.NumEdges = len(edges)
            mesh.NumFaces = len(faces)
            mesh.save()
            for key, value in edges.items():
                for item in value:
                    obj = Nodes.objects.filter(NodeNum=item, mesh_id=mesh.id)
                    obj.update(EdgeGroup=key)

            for key, value in faces.items():
                for item in value:
                    obj = Nodes.objects.filter(NodeNum=item, mesh_id=mesh.id)
                    obj.update(FaceGroup=key)

            return redirect('meshdisplay', slug=analysis.name, pk=mesh.id)
    else:
        form = NewMeshForm()
    Page = SideBarPage().DicUpdate("")
    return render(request, 'mesh.html', PageVariables(Page,form,analysis))

def display_mesh(request, slug, pk):

    analysis = get_object_or_404(Analysis, name=slug)   
    nodes = Nodes.objects.filter(mesh_id=pk)
    table = Connectivity.objects.filter(mesh_id=pk)
    div = PlotlyPlot(nodes, table, None)
    
    if request.method == 'POST':
        form = MeshConfirmationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if cd['like'] == 'yes':
                return redirect('resin', slug=analysis.name)
            else:
                Mesh.objects.filter(id=pk).delete()
                return redirect('mesh', slug=analysis.name)
    else:
        form = MeshConfirmationForm()
    Page = SideBarPage().DicUpdate("mesh")
    dic=PageVariables(Page,form,analysis)
    dic['graph']=div
    return render(request, 'meshdisplay.html', dic)



def resin_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewResinForm(request.POST)
        if form.is_valid():
            resin = form.save(commit=False)
            resin.analysis = analysis
            resin.save()
            return redirect('preform', slug=analysis.name)
    else:
        form = NewResinForm()
    Page = SideBarPage().DicUpdate("resin")
    return render(request, 'resin.html', PageVariables(Page,form,analysis))


def preform_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewPreformForm(request.POST)
        if form.is_valid():
            preform = form.save(commit=False)
            preform.analysis = analysis
            val = form.cleaned_data
            if val['btn']=="add":
                preform.save()
                form = NewPreformForm(initial={'name':"Preform_{}".format(len(analysis.preform.all())+1)})
            elif val['btn']=="proceed":
                return redirect('section', slug=analysis.name)
    else:
        form = NewPreformForm(initial={'name':"Preform_{}".format(len(analysis.preform.all())+1)})
    Page = SideBarPage().DicUpdate("preform")
    return render(request, 'preform.html', PageVariables(Page,form,analysis))


def section_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewSectionForm(request.POST, analysis=analysis)
        if form.is_valid():
            section = form.save(commit=False)
            section.analysis = analysis
            section.save()
            return redirect('step', slug=analysis.name)
    else:
        form = NewSectionForm(analysis=analysis)
    Page = SideBarPage().DicUpdate("section")
    return render(request, 'section.html', PageVariables(Page,form,analysis))


def step_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.analysis = analysis
            step.save()

            return redirect('bc', slug=analysis.name)
    else:
        form = NewStepForm()
    Page = SideBarPage().DicUpdate("step")
    return render(request,'step.html', PageVariables(Page,form,analysis))


def bc_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewBCForm(request.POST, mesh=analysis.mesh)
        if form.is_valid():
            bc = form.save(commit=False)
            bc.analysis = analysis
            val = form.cleaned_data
            exist=False
            if val['btn']=="add":
                # check if the value exist and update it
                for bc_data in analysis.bc.values():
                    if bc.name in bc_data['name']:
                        exist=True
                        Update_key=bc_data['id']
                        Update_name=bc.name
                if exist:
                    messages.warning(request, 'Boundary condition updated!'.format(Update_name))
                    UpdateBC=BC.objects.get(id=Update_key)
                    UpdateBC.value = bc.value
                    UpdateBC.typ = bc.typ
                    UpdateBC.save()
                else:
                    bc.save( )
                form = NewBCForm(request.POST, mesh=analysis.mesh)
            elif val['btn']=="proceed":
                if len(analysis.bc.values())==analysis.mesh.NumEdges:
                    return redirect('submit', slug=analysis.name)
                else:
                    messages.warning(request, 'Please assign all boundary conditions')
                    form = NewBCForm(request.POST, mesh=analysis.mesh)

    else:
        form = NewBCForm(mesh=analysis.mesh)
    Page = SideBarPage().DicUpdate("bc")
    return render(request, 'bc.html', PageVariables(Page,form,analysis))


def submit_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = JobSubmitForm(request.POST)
        Results.objects.create(analysis=analysis)
        return redirect('result', slug=analysis.name)
    else:
        form = JobSubmitForm()
    Page = SideBarPage().DicUpdate("submit")
    return render(request, 'submit.html', PageVariables(Page,form,analysis))


def result_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    Page = SideBarPage().DicUpdate("results")
    nodes = Nodes.objects.filter(mesh_id=analysis.mesh.id)
    table = Connectivity.objects.filter(mesh_id=analysis.mesh.id)
    results=Contour(analysis.mesh.address)
    step=int(analysis.results.Step)
    results_contour=results.IntensityReader(step)
    if request.method == 'POST':
        form = ResultsForm(request.POST)
        if form.is_valid():
            val = form.cleaned_data
            if val['btn'] == 'Next':
                step+=1

                try:
                    results_contour=results.IntensityReader(step)
                    NewStep=Results.objects.get(analysis=analysis)
                    NewStep.Step=step
                    NewStep.save()
                except:
                    step-=1
                    results_contour=results.IntensityReader(step)
                    messages.warning(request, 'Last Step')
            elif val['btn'] == 'Previous':
                step-=1
                try:
                    results_contour=results.IntensityReader(step)
                    NewStep=Results.objects.get(analysis=analysis)
                    NewStep.Step=step
                    NewStep.save()
                except:
                    step+=1
                    results_contour=results.IntensityReader(step)
                    messages.warning(request, 'First Step')
    else:
        form = ResultsForm()
    div = PlotlyPlot(nodes, table, results_contour)
    dic=PageVariables(Page,form,analysis)
    dic['graph']=div
    dic['step']=step
    return render(request, 'result.html', dic)
