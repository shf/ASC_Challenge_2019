import colorlover as cl
import plotly.graph_objs as go
import plotly.offline as opy
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (NewAnalysisForm, NewBCForm, NewMeshForm, MeshConfirmationForm, NewPreformForm,
                    NewResinForm, NewSectionForm, NewStepForm)
from .models import (BC, Analysis, Connectivity, Mesh, Nodes, Preform, Resin,
                     Section, Step)
from .solver.Importers import MeshImport

def PlotlyPlot (nodes, table):
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
        ii.append(line["N1"]-1)
        jj.append(line["N2"]-1)
        kk.append(line["N3"]-1)

    # define lines of each element
    x_line = []
    y_line = []
    z_line = []
    for t in range(len(ii)):
        elem = [ii[t], jj[t], kk[t], ii[t]]
        x_line.extend([xn[v] for v in elem]+[None])
        y_line.extend([yn[v] for v in elem]+[None])
        z_line.extend([zn[v] for v in elem]+[None])

    figure = go.Figure(data=[
        go.Mesh3d(
            x=xn,
            y=yn,
            z=zn,
            showscale=False,
            color='darkturquoise',

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


def home(request):
    analyses = Analysis.objects.all()
    if request.method == 'POST':
        form = NewAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.save()

            return redirect('mesh', slug=analysis.name)
    else:
        form = NewAnalysisForm()
    return render(request, 'home.html', {'form': form})


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
    return render(request, 'mesh.html', {'analysis': analysis, 'form': form})

def display_mesh(request, slug, pk):

    analysis = get_object_or_404(Analysis, name=slug)   
    nodes = Nodes.objects.filter(mesh_id=pk)
    table = Connectivity.objects.filter(mesh_id=pk)
    div = PlotlyPlot(nodes, table)
    
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

    return render(request, 'meshdisplay.html', {'analysis': analysis, 'graph': div, 'form': form})



def resin_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    mesh = get_object_or_404(Mesh, analysis_id=analysis.id)
    if request.method == 'POST':
        form = NewResinForm(request.POST)
        if form.is_valid():
            resin = form.save(commit=False)
            resin.analysis = analysis
            resin.save()
            return redirect('preform', slug=analysis.name)
    else:
        form = NewResinForm()
    return render(request, 'resin.html', {'analysis': analysis, 'mesh': mesh, 'form': form})
 

def preform_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewPreformForm(request.POST)
        if form.is_valid():
            preform = form.save(commit=False)
            preform.analysis = analysis
            preform.save()

            return redirect('section', slug=analysis.name)
    else:
        form = NewPreformForm()
    return render(request, 'preform.html', {'analysis': analysis, 'mesh': analysis.mesh, 'resin': analysis.resin, 'form': form})


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
    return render(request, 'section.html',
                  {'analysis': analysis, 'mesh': analysis.mesh, 'resin': analysis.resin,
                      'preforms': analysis.preform.all(), 'form': form}
                  )


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
    return render(
        request, 'step.html',
        {'analysis': analysis, 'mesh': analysis.mesh, 'resin': analysis.resin,
         'preforms': analysis.preform.all(), 'sections': analysis.section.all(), 'form': form}
    )


def bc_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewBCForm(request.POST)
        if form.is_valid():
            bc = form.save(commit=False)
            bc.analysis = analysis
            bc.save()

            return redirect('submit', slug=analysis.name)
    else:
        form = NewBCForm()
    return render(
        request, 'bc.html',
        {'analysis': analysis, 'mesh': analysis.mesh, 'resin': analysis.resin,
         'preforms': analysis.preform.all(), 'sections': analysis.section.all(),
         'step': analysis.step, 'form': form}
    )


def submit_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        return redirect('result', slug=analysis.name)
    return render(
        request, 'submit.html',
        {'analysis': analysis, 'mesh': analysis.mesh, 'resin': analysis.resin,
         'preforms': analysis.preform.all(), 'sections': analysis.section.all(),
         'step': analysis.step, 'bcs': analysis.bc.all()}
    )


def result_page(request, slug):
    return render(request, 'result.html')


