from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from .models import Analysis
from .models import Mesh
from .models import Material
from .models import Section
from .models import Step
from .models import BC

from .forms import NewAnalysisForm
from .forms import NewMeshForm
from .forms import NewMaterialForm
from .forms import NewSectionForm


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

            return redirect('material', slug = analysis.name)
    else:
        form = NewMeshForm()
    return render(request, 'mesh.html', {'analysis': analysis, 'form': form}) 

def material_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewMaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.analysis = analysis
            material.save()

            return redirect('section', slug = analysis.name) 
    else:
        form = NewMaterialForm()
    return render(request, 'material.html', {'analysis': analysis, 'mesh':analysis.mesh, 'form': form})

def section_page(request, slug):
    analysis = get_object_or_404(Analysis, name = slug)
    if request.method == 'POST':
        form = NewSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.analysis = analysis
            section.save()

            return redirect('step', slug = analysis.name) 
    else:
        form = NewSectionForm()
    return render(request, 'section.html', {'analysis': analysis, 'mesh':analysis.mesh, 'materials':analysis.material.all(), 'form': form})

def step_page(request, slug):
    return render(request, 'step.html')

def bc_page(request, slug):
    return render(request, 'bc.html')

def submit_page(request, slug):
    return render(request, 'submit.html')

def result_page(request, slug):
    return render(request, 'result.html')