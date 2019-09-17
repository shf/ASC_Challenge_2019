import json
import os
import subprocess
import time
import numpy as np
import celery
import plotly.graph_objs as go
import colorlover as cl
import plotly.offline as opy
from celery import current_app
from celery.result import AsyncResult
from celery.task.control import revoke
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaulttags import register


from .forms import (StartApp, JobSubmitForm, MeshConfirmationForm, NewAnalysisForm,
                    NewBCForm, NewMeshForm, NewPreformForm, NewResinForm,
                    NewSectionForm, NewStepForm, ResultsForm, StatusForm)
from .models import (BC, Analysis, Connectivity, Mesh, Nodes, Preform, Resin,
                     Results, Section, Step)
from .solver.Solver_Hub import Darcy_CVFEM, print_conf, create_conf, solver_rtm, solver_hp_rtm
from .solver.Importers import Contour, MeshImport


def PlotlyPlot(nodes, table, NumFace):

    # nodes
    xn = []
    yn = []
    zn = []
    for node in nodes.values():
        xn.append(node["x"])
        yn.append(node["y"])
        zn.append(node["z"])

    # connectivity
    ii = []
    jj = []
    kk = []
    FaceColor = []
    colors = cl.to_rgb(cl.interp(cl.scales[str(5)]['div']['RdYlBu'],NumFace))
    palette = {}
    for n, item in enumerate(table.values('FaceGroup').distinct()):
        palette [item['FaceGroup']] = colors[n]
    for element in table.values():
        ii.append(element["N1"])
        jj.append(element["N2"])
        kk.append(element["N3"])
        FaceColor.append(palette[element['FaceGroup']])

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
            hoverinfo='skip',
            facecolor=FaceColor,
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
            autosize=True,
            scene=dict(
                xaxis=dict(
                    visible=True
                ),
                yaxis=dict(
                    visible=True
                ),
                zaxis=dict(
                    visible=True
                ),
                aspectmode='data',
                camera=dict(
                    eye=dict(x=2, y=2, z=2)
                )
            ),
    )
    )

    return opy.plot(figure, auto_open=False, output_type='div'), palette

# dictionary for returning face color for each face in template
@register.filter
def face_color(dictionary, key):    
    return dictionary[key]

# dictionary for sidebar switching
@register.filter
def get_active(dictionary, key):
    return dictionary.get(key)[0]


@register.filter
def get_show(dictionary, key):
    return dictionary.get(key)[1]


class SideBarPage():
    def __init__(self):
        self._page = {
            'mesh': ["<li class=\"nav-item\">", "<div id=\"collapse_mesh\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'resin': ["<li class=\"nav-item\">", "<div id=\"collapse_resin\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'preform': ["<li class=\"nav-item\">", "<div id=\"collapse_preform\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'section': ["<li class=\"nav-item\">", "<div id=\"collapse_section\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'step': ["<li class=\"nav-item\">", "<div id=\"collapse_step\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'bc': ["<li class=\"nav-item\">", "<div id=\"collapse_bc\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'submit': ["<li class=\"nav-item\">", "<div id=\"collapse_submit\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"],
            'results': ["<li class=\"nav-item\">", "<div id=\"collapse_submit\" class=\"collapse\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">"]
        }

    def DicUpdate(self, page):
        self._page[page] = ['<li class=\"nav-item active\">',
                            "<div id=\"collapse_{}\" class=\"collapse show\" aria-labelledby=\"headingUtilities\"data-parent=\"#accordionSidebar\">".format(page)]
        return self._page

# variables to pass in all views


class NoObject():
    def __init__(self, _name):
        self._name = _name

    @property
    def name(self):
        return self._name


def PageVariables(Page, form, analysis):
    ViewsVars = {'page': Page,
                 'form': form,
                 'analysis': analysis,
                 'preforms': analysis.preform.all(),
                 'sections': analysis.section.all(),
                 'bc': analysis.bc.all()}
    try:
        ViewsVars['mesh'] = analysis.mesh
    except:
        ViewsVars['mesh'] = NoObject("Empty")
    try:
        ViewsVars['resin'] = analysis.resin
    except:
        ViewsVars['resin'] = NoObject("Empty")
    try:
        ViewsVars['step'] = analysis.step
    except:
        ViewsVars['step'] = NoObject("Empty")
    return ViewsVars

# views:


def home(request):
    if request.method == 'POST':
        form = StartApp(request.POST)
        if form.is_valid():
            val=form.cleaned_data
            if val['btn'] == 'run':
                return redirect('apphome')
            elif val['btn'] == 'docs':
                return redirect("https://github.com/shf/ASC_Challenge/wiki")
    else:
        form = StartApp()
    return render(request, 'home.html')

def apphome(request):
    analysis = Analysis.objects.all()
    if request.method == 'POST':
        form = NewAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.name=analysis.name.replace(" ", "_")
            analysis.save()

            return redirect('meshupload', slug=analysis.name)
    else:
        form = NewAnalysisForm(initial={'name': "Analysis_{}".format(len(analysis))})
    Page = SideBarPage().DicUpdate("")
    return render(request, 'apphome.html', {'page': Page, 'form': form})

def mesh_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewMeshForm(request.POST, request.FILES)
        if form.is_valid():
            MeshFile = form.cleaned_data
            MeshFile['analysis_id'] = analysis.id
            if Mesh.objects.filter(analysis=analysis).exists():
                Nodes.objects.filter(mesh_id=analysis.mesh.id).delete()
                Connectivity.objects.filter(mesh_id=analysis.mesh.id).delete()
                Mesh.objects.filter(analysis=analysis).delete()
                os.remove(os.path.join(settings.MEDIA_ROOT, str(analysis.id), 'mesh.xml'))
            Mesh.objects.update_or_create(MeshFile, analysis=analysis)
            mesh = get_object_or_404(Mesh, analysis_id=analysis.id)

            # mesh name from file name
            mesh.name = str(mesh.address).split("/")[1].split(".")[0]

            # save mesh in xml format
            MeshImp = MeshImport(os.path.join(settings.MEDIA_ROOT, str(mesh.address)))
            MeshImp.UNVtoXMLConverter()

            # edges and faces should be extracted before calling for nodes and table
            edges, faces = MeshImp.MeshGroups()
            mesh.NumEdges = len(edges)
            mesh.NumFaces = 1 if len(faces) == 0 else len(faces)

            # save mesh data in database
            nodes, ConnectivityTable = MeshImp.MeshData()
            for key, value in nodes.items():
                Nodes.objects.create(NodeNum=int(key), x=float(
                    value[0]), y=float(value[1]), z=float(value[2]), mesh=mesh)
            for key, value in ConnectivityTable.items():
                Connectivity.objects.create(ElmNum=int(key), N1=float(
                    value[0]), N2=float(value[1]), N3=float(value[2]), mesh=mesh)
            mesh.save()
            for key, value in edges.items():
                for item in value:
                    obj = Nodes.objects.filter(NodeNum=item, mesh_id=mesh.id)
                    obj.update(EdgeGroup=key)

            for key, value in faces.items():
                for item in value:
                    obj = Connectivity.objects.filter(ElmNum=item, mesh_id=mesh.id)
                    obj.update(FaceGroup=key)

            return redirect('meshdisplay', slug=analysis.name)
    else:
        form = NewMeshForm()
    Page = SideBarPage().DicUpdate("")
    return render(request, 'mesh.html', PageVariables(Page, form, analysis))


def display_mesh(request, slug):

    analysis = get_object_or_404(Analysis, name=slug)
    nodes = Nodes.objects.filter(mesh_id=analysis.mesh.id)
    table = Connectivity.objects.filter(mesh_id=analysis.mesh.id)
    div, palette = PlotlyPlot(nodes, table, analysis.mesh.NumFaces)
    if request.method == 'POST':
        form = MeshConfirmationForm(request.POST)
        if form.is_valid():
            val = form.cleaned_data
            if val['btn'] == 'confirm':
                return redirect('resin', slug=analysis.name)
            elif val['btn'] == 'upload':
                return redirect('meshupload', slug=analysis.name)
    else:
        form = MeshConfirmationForm()
    Page = SideBarPage().DicUpdate("mesh")
    dic = PageVariables(Page, form, analysis)
    dic['graph'] = div
    dic['Edges'] = nodes.values('EdgeGroup').distinct()
    dic['Faces'] = [face['FaceGroup'] for face in table.values('FaceGroup').distinct()]
    dic['palette'] = palette
    return render(request, 'meshdisplay.html', dic)


def resin_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    
    if Resin.objects.filter(analysis_id=analysis.id).exists():
        init = list(Resin.objects.filter(
            analysis_id=analysis.id).values())[0]
    else:
        init={'name':'Resin_1', 'viscosity':0.02}
    if request.method == 'POST':
        form = NewResinForm(request.POST, initial=init)
        if form.is_valid():
            resin = form.cleaned_data
            resin['analysis_id'] = analysis.id
            Resin.objects.update_or_create(resin, analysis=analysis)
            return redirect('preform', slug=analysis.name)
    else:
        form = NewResinForm(initial=init)
    Page = SideBarPage().DicUpdate("resin")
    return render(request, 'resin.html', PageVariables(Page, form, analysis))


def preform_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewPreformForm(request.POST)
        if form.is_valid():
            preform = form.save(commit=False)
            preform.analysis = analysis
            val = form.cleaned_data
            if val['btn'] == "add":
                if Preform.objects.filter(name=val['name']).exists():
                    Preform.objects.filter(name=val['name']).delete()
                preform.save()
                form = NewPreformForm(
                    initial={'name': "Preform_{}".format(len(analysis.preform.all())+1)})
            elif val['btn'] == "proceed":
                return redirect('section', slug=analysis.name)
    else:
        form = NewPreformForm(
            initial={'name': "Preform_{}".format(len(analysis.preform.all())+1)})
    Page = SideBarPage().DicUpdate("preform")
    return render(request, 'preform.html', PageVariables(Page, form, analysis))


def section_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewSectionForm(
            request.POST, analysis=analysis, mesh=analysis.mesh)
        if form.is_valid():
            section = form.save(commit=False)
            section.analysis = analysis
            val = form.cleaned_data
            if val['btn'] == "add":
                section.save()
                form = NewSectionForm(
                    request.POST, analysis=analysis, mesh=analysis.mesh)
            elif val['btn'] == "proceed":
                if len(analysis.section.values('name').distinct()) == analysis.mesh.NumFaces:
                    return redirect('bc', slug=analysis.name)
            elif val['btn'] == "Delete":
                if Section.objects.filter(name=val['name']).exists():
                    Section.objects.filter(name=val['name']).delete()
                else:
                    messages.warning(request, 'Please assign all sections')
                    form = NewSectionForm(
                        request.POST, analysis=analysis, mesh=analysis.mesh)
    else:
        form = NewSectionForm(analysis=analysis, mesh=analysis.mesh)
    Page = SideBarPage().DicUpdate("section")
    return render(request, 'section.html', PageVariables(Page, form, analysis))


def step_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)

    if Step.objects.filter(analysis_id=analysis.id).exists():
        init = list(Step.objects.filter(
            analysis_id=analysis.id).values())[0]
    else:
        init={'name':'Step_1', 'typ':0, 'endtime':1000, 'outputstep':0.01, 
            'maxiterations':10000, 'maxhaltsteps':10, 'minchangesaturation':0.001, 
            'timescaling':2.0, 'fillthreshold':0.999}
    if request.method == 'POST':
        form = NewStepForm(request.POST, initial=init)
        if form.is_valid():
            step = form.cleaned_data
            step['analysis_id'] = analysis.id
            Step.objects.update_or_create(step, analysis=analysis)
            return redirect('submit', slug=analysis.name)
    else:
        form = NewStepForm(initial=init)
    Page = SideBarPage().DicUpdate("step")
    return render(request, 'step.html', PageVariables(Page, form, analysis))


def bc_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = NewBCForm(request.POST, mesh=analysis.mesh)
        if form.is_valid():
            bc = form.save(commit=False)
            bc.analysis = analysis
            val = form.cleaned_data
            exist = False
            if val['btn'] == "add":
                # check if the value exist and update it
                for bc_data in analysis.bc.values():
                    if bc.name in bc_data['name']:
                        exist = True
                        Update_key = bc_data['id']
                        Update_name = bc.name
                if exist:
                    messages.warning(
                        request, 'Boundary condition updated!'.format(Update_name))
                    UpdateBC = BC.objects.get(id=Update_key)
                    UpdateBC.value = bc.value
                    UpdateBC.typ = bc.typ
                    UpdateBC.condition = bc.condition
                    UpdateBC.save()
                else:
                    bc.save()
                form = NewBCForm(request.POST, mesh=analysis.mesh)
            elif val['btn'] == "proceed":
                if len(analysis.bc.values()) == analysis.mesh.NumEdges:
                    return redirect('step', slug=analysis.name)
                else:
                    messages.warning(
                        request, 'Please assign all boundary conditions')
                    form = NewBCForm(request.POST, mesh=analysis.mesh)

    else:
        form = NewBCForm(mesh=analysis.mesh)
    Page = SideBarPage().DicUpdate("bc")
    return render(request, 'bc.html', PageVariables(Page, form, analysis))

def submit_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = JobSubmitForm(request.POST)
        if form.is_valid():
            val = form.cleaned_data
            if val['btn'] == 'submit':
                solver = solver_rtm.delay(analysis.id)
                Results.objects.update_or_create(analysis=analysis)
                Results.objects.filter(analysis=analysis).update(processID=solver.id)
                return redirect('status', slug=analysis.name)
            elif val['btn'] == 'download_conf':
                InputData = create_conf(analysis.id)
                print_conf(InputData)
                file_path = os.path.join(settings.MEDIA_ROOT, str(analysis.id), 'config.db')
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fh:
                        response = HttpResponse(fh.read(), content_type="xml")
                        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                        return response
                raise Http404
            elif val['btn'] == 'download_UNV':
                file_path = os.path.join(settings.MEDIA_ROOT, str(analysis.mesh.address))
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fh:
                        response = HttpResponse(fh.read(), content_type="unv")
                        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                        return response
                raise Http404
            elif val['btn'] == 'download_XML':
                file_path = os.path.join(settings.MEDIA_ROOT, str(analysis.id), 'mesh.xml')
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fh:
                        response = HttpResponse(fh.read(), content_type="xml")
                        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                        return response
                raise Http404
    else:
        form = JobSubmitForm()
    Page = SideBarPage().DicUpdate("submit")
    return render(request, 'submit.html', PageVariables(Page, form, analysis))


def get_progress(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    task_id = analysis.results.processID
    result = AsyncResult(task_id)
    response_data = {
        'state': result.state,
        'details': result.info,
    }
    return HttpResponse(json.dumps(response_data), content_type='ASC_Project/json')


def status_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            val = form.cleaned_data
            if val['btn'] == "kill":
                revoke(analysis.results.processID, terminate=True)
                return redirect('submit', slug=analysis.name)
            elif val['btn'] == "result":
                return redirect('result', slug=analysis.name)
    else:
        form = StatusForm()
    Page = SideBarPage().DicUpdate("submit")
    return render(request, 'status.html', PageVariables(Page, form, analysis))

def result_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    directory = os.path.abspath(os.path.join(os.getcwd(), '..'))
    # modifying the paraview server configuration
    with open(directory + '/ParaView-5.7.0/launcher.config', 'r') as conf:
        data = conf.readlines()
    data[44] = "            \"--data\", \"{}/ASC_Project/media/{}/results/\",\n".format(
        directory, analysis.id)

    with open(directory + '/ParaView-5.7.0/launcher.config', 'w') as conf:
        conf.writelines(data)

    # kill previously run server
    # this allows for just one concurrent result,
    subprocess.call(['killall', 'pvpython'])
    os.system('rm -f {}/ParaView-5.7.0/viz-logs/*.txt'.format(directory))
    # run new server with modified configuration
    p = subprocess.Popen([directory + '/ParaView-5.7.0/bin/pvpython',
                          directory + '/ParaView-5.7.0/lib/python3.7/site-packages/wslink/launcher.py',
                          directory + '/ParaView-5.7.0/launcher.config'],
                         )
    time.sleep(2)
    # save the process id to database, might be useful for concurrent visulization
    analysis.results.processID = p.pid
    analysis.results.save()
    Page = SideBarPage().DicUpdate("results")
    form = "form"
    dic = PageVariables(Page, form, analysis)
    dic['paraview'] = "http://127.0.0.1:8080/"
    return render(request, 'result.html', dic)


def result_old_page(request, slug):
    analysis = get_object_or_404(Analysis, name=slug)
    Page = SideBarPage().DicUpdate("results")
    nodes = Nodes.objects.filter(mesh_id=analysis.mesh.id)
    table = Connectivity.objects.filter(mesh_id=analysis.mesh.id)
    results = Contour(analysis.mesh.address)
    step = int(analysis.results.Step)
    results_contour = results.IntensityReader(step)
    if request.method == 'POST':
        form = ResultsForm(request.POST)
        if form.is_valid():
            val = form.cleaned_data
            if val['btn'] == 'Next':
                step += 1

                try:
                    results_contour = results.IntensityReader(step)
                    NewStep = Results.objects.get(analysis=analysis)
                    NewStep.Step = step
                    NewStep.save()
                except:
                    step -= 1
                    results_contour = results.IntensityReader(step)
                    messages.warning(request, 'Last Step')
            elif val['btn'] == 'Previous':
                step -= 1
                try:
                    results_contour = results.IntensityReader(step)
                    NewStep = Results.objects.get(analysis=analysis)
                    NewStep.Step = step
                    NewStep.save()
                except:
                    step += 1
                    results_contour = results.IntensityReader(step)
                    messages.warning(request, 'First Step')
    else:
        form = ResultsForm()
    div = PlotlyPlot(nodes, table, results_contour)
    dic = PageVariables(Page, form, analysis)
    dic['graph'] = div
    dic['step'] = step
    return render(request, 'result_old.html', dic)
