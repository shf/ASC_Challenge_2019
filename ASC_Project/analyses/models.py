from django.db import models
from django.contrib.auth.models import User

from .choice import TYPE_OF_ANALYSIS
from .choice import TYPE_OF_BC
from .choice import CONDITION_OF_BC

from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator

# this function defines a specific folder for the files required in analyses
def analysis_directory_path(instance,filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{}/{}'.format(instance.analysis.id,filename)

class Analysis(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of analysis (do not use space)')
    description = models.CharField(max_length=200, help_text='Description')

    def __str__(self):
        return self.name

class Mesh(models.Model):
    name = models.CharField(max_length= 100, default="_None")
    analysis = models.OneToOneField(Analysis, related_name='mesh', on_delete=models.CASCADE)
    address = models.FileField(upload_to=analysis_directory_path, help_text='The layout should be primarily in x-y plane.', 
        validators=[FileExtensionValidator(allowed_extensions=['unv'])])
    NumFaces = models.IntegerField(default=1)
    NumEdges = models.IntegerField(default=1)

    def __str__(self):
        return self.name

class Nodes(models.Model):
    NodeNum = models.IntegerField()
    x = models.FloatField(null=True,max_length=6)
    y = models.FloatField(null=True,max_length=6)
    z = models.FloatField(null=True,max_length=6)
    EdgeGroup=models.CharField(max_length=50, default="_None")
    mesh = models.ForeignKey(Mesh, on_delete=models.CASCADE)

    def __str__(self):
        return "Nodes of {}".format(self.mesh)

class Connectivity(models.Model):
    ElmNum = models.IntegerField(null=True)
    N1 = models.IntegerField(null=True)
    N2 = models.IntegerField(null=True)
    N3 = models.IntegerField(null=True)
    FaceGroup = models.CharField(max_length=300, default="AllDomain")
    mesh = models.ForeignKey(Mesh, on_delete=models.CASCADE)

    def __str__(self):
        return "Connectivity table of {}".format(self.mesh)



class Resin(models.Model):
    name = models.CharField(max_length=30, help_text='Name of Resin')
    viscosity = models.FloatField(help_text='Enter a number for viscosity', 
            validators=[
            MinValueValidator(0),
        ])
    analysis = models.OneToOneField(Analysis, related_name='resin', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Preform(models.Model):
    name = models.CharField(max_length=30, help_text='Name of Preform')
    thickness = models.FloatField(default=0.01, help_text='Thickness of preform', 
            validators=[
            MinValueValidator(0),
        ])
    K11 = models.FloatField(default=1e-10, help_text='Enter a number for K11 (permeability in the 1st principal direction)', 
            validators=[
            MinValueValidator(0),
        ])
    K12 = models.FloatField(default=0, help_text='Enter a number for K12', 
            validators=[
            MinValueValidator(0),
        ])
    K22 = models.FloatField(default=2e-10, help_text='Enter a number for K22 (permeability in the 2nd principal direction)', 
            validators=[
            MinValueValidator(0),
        ])
    phi = models.FloatField(default=0.5, help_text='Enter a value between 0 and 1 for the volume fraction of fibers', 
            validators=[
            MaxValueValidator(1),
            MinValueValidator(0)
        ])
    analysis = models.ForeignKey(Analysis, related_name='preform', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=30)
    preform = models.ForeignKey(Preform, related_name='preform', on_delete=models.SET_NULL, null=True)
    rotate = models.FloatField(default=0, help_text='Degree of rotation of 1st axis with respect to x axis', 
            validators=[
            MinValueValidator(0),
            MaxValueValidator(180),
        ])
    analysis = models.ForeignKey(Analysis, related_name='section', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Step(models.Model):
    name = models.CharField(max_length=30)
    typ = models.CharField(max_length=30, choices=TYPE_OF_ANALYSIS)
    endtime = models.FloatField(
            validators=[
            MinValueValidator(0),
        ])
    outputstep = models.FloatField(
            validators=[
            MinValueValidator(0),
        ])
    maxiterations = models.IntegerField(
            validators=[
            MinValueValidator(0),
        ])
    maxhaltsteps = models.IntegerField(
            validators=[
            MinValueValidator(0),
        ])
    minchangesaturation = models.FloatField(
            validators=[
            MinValueValidator(0),
        ])
    timescaling = models.FloatField()
    fillthreshold = models.FloatField()
    analysis = models.OneToOneField(Analysis, related_name='step', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class BC(models.Model):
    name = models.CharField(max_length=30)
    typ = models.CharField(max_length=30, choices=TYPE_OF_BC, default=0)
    condition = models.CharField(max_length=30, choices=CONDITION_OF_BC, default=0)
    value = models.FloatField(default=0, help_text='Value on Boundary Condition')
    analysis = models.ForeignKey(Analysis, related_name='bc', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Results(models.Model):
    
    processID=models.CharField(default=0,max_length=30)
    analysis = models.OneToOneField(Analysis, related_name='results', on_delete=models.CASCADE)
