from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from .models import Analysis
from .models import Mesh
from .models import Resin
from .models import Preform
from .models import Section
from .models import Step
from .models import BC

from .forms import NewAnalysisForm
from .forms import NewMeshForm
from .forms import NewResinForm
from .forms import NewPreformForm
from .forms import NewSectionForm
from .forms import NewStepForm
from .forms import NewBCForm


def home(request):
    analyses = Analysis.objects.all()
    if request.method == 'POST':
        form = NewAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.save()

            return redirect('mesh', slug = analysis.name) 
    else:
        form = NewAnalysisForm()
    return render(request, 'home.html', {'form': form})

def mesh_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewMeshForm(request.POST, request.FILES)
        if form.is_valid():
            mesh = form.save(commit=False)
            mesh.analysis = analysis
            mesh.save()

            return redirect('resin', slug = analysis.name)
    else:
        form = NewMeshForm()
    return render(request, 'mesh.html', {'analysis': analysis, 'form': form}) 

def resin_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewResinForm(request.POST)
        if form.is_valid():
            resin = form.save(commit=False)
            resin.analysis = analysis
            resin.save()

            return redirect('preform', slug = analysis.name) 
    else:
        form = NewResinForm()
    return render(request, 'resin.html', {'analysis': analysis, 'mesh':analysis.mesh, 'form': form})

def preform_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewPreformForm(request.POST)
        if form.is_valid():
            preform = form.save(commit=False)
            preform.analysis = analysis
            preform.save()

            return redirect('section', slug = analysis.name) 
    else:
        form = NewPreformForm()
    return render(request, 'preform.html', {'analysis': analysis, 'mesh':analysis.mesh, 'resin':analysis.resin, 'form': form})

def section_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewSectionForm(request.POST, analysis=analysis)
        if form.is_valid():
            section = form.save(commit=False)
            section.analysis = analysis
            section.save()

            return redirect('step', slug = analysis.name) 
    else:
        form = NewSectionForm(analysis=analysis)
    return render(request, 'section.html', 
            {'analysis': analysis, 'mesh':analysis.mesh, 'resin':analysis.resin, 'preforms':analysis.preform.all(), 'form': form}
        )

def step_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.analysis = analysis
            step.save()

            return redirect('bc', slug = analysis.name) 
    else:
        form = NewStepForm()
    return render(
            request, 'step.html', 
            {'analysis': analysis, 'mesh':analysis.mesh, 'resin':analysis.resin, 
            'preforms':analysis.preform.all(), 'sections':analysis.section.all(), 'form': form}
        )

def bc_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewBCForm(request.POST)
        if form.is_valid():
            bc = form.save(commit=False)
            bc.analysis = analysis
            bc.save()

            return redirect('submit', slug = analysis.name) 
    else:
        form = NewBCForm()
    return render(
            request, 'bc.html', 
            {'analysis': analysis, 'mesh':analysis.mesh, 'resin':analysis.resin, 
            'preforms':analysis.preform.all(), 'sections':analysis.section.all(), 
            'step':analysis.step, 'form': form}
        )

def submit_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        return redirect('result', slug = analysis.name) 
    return render(
            request, 'submit.html', 
            {'analysis': analysis, 'mesh':analysis.mesh, 'resin':analysis.resin, 
            'preforms':analysis.preform.all(), 'sections':analysis.section.all(), 
            'step':analysis.step, 'bcs':analysis.bc.all()}
        )

def result_page(request, slug):
    return render(request, 'result.html')

import plotly.offline as opy
import plotly.graph_objs as go

def display_mesh(request):
    x = [-2,0,4,6,7]
    y = [q**2-q+3 for q in x]
    trace1 = go.Scatter(x=x, y=y, marker={'color': 'red', 'symbol': 104, 'size': 10},
                        mode="lines",  name='1st Trace')
    data=go.Data([trace1])
    layout=go.Layout(title="Meine Daten", xaxis={'title':'x1'}, yaxis={'title':'x2'})
    figure=go.Figure(data=data,layout=layout)
    div = opy.plot(figure, auto_open=False, output_type='div')
    return render(request, 'meshdisplay.html', {'graph': div})