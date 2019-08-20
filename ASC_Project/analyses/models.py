from django.db import models
from django.contrib.auth.models import User

from .choice import TYPE_OF_ANALYSIS
from .choice import TYPE_OF_BC

# this function defines a specific folder for the files required in analyses
def analysis_directory_path(instance,filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{}/{}'.format(instance.analysis.id,filename)

class Analysis(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of analysis')
    description = models.CharField(max_length=200, help_text='Description')

    def __str__(self):
        return self.name

class Mesh(models.Model):
    name = models.CharField(max_length= 100, default="_None")
    analysis = models.OneToOneField(Analysis, related_name='mesh', on_delete=models.CASCADE)
    address = models.FileField(upload_to=analysis_directory_path)
    NumFaces = models.IntegerField(default=1)
    NumEdges = models.IntegerField(default=1)

    def __str__(self):
        return self.name

class Nodes(models.Model):
    NodeNum = models.IntegerField()
    x = models.FloatField(null=True,max_length=6)
    y = models.FloatField(null=True,max_length=6)
    z = models.FloatField(null=True,max_length=6)
    FaceGroup=models.CharField(max_length=50, default="_None")
    EdgeGroup=models.CharField(max_length=50, default="_None")
    mesh = models.ForeignKey(Mesh, on_delete=models.CASCADE)

    def __str__(self):
        return "Nodes of {}".format(self.mesh)

class Connectivity(models.Model):
    ElmNum = models.IntegerField(null=True)
    N1 = models.IntegerField(null=True)
    N2 = models.IntegerField(null=True)
    N3 = models.IntegerField(null=True)
    mesh = models.ForeignKey(Mesh, on_delete=models.CASCADE)

    def __str__(self):
        return "Connectivity table of {}".format(self.mesh)



class Resin(models.Model):
    name = models.CharField(max_length=30, help_text='Name of Resin')
    viscosity = models.FloatField(default=0.02, help_text='Enter a number for viscosity')
    analysis = models.OneToOneField(Analysis, related_name='resin', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Preform(models.Model):
    name = models.CharField(max_length=30, help_text='Name of Preform')
    thickness = models.FloatField(default=0.01, help_text='Thickness')
    K11 = models.FloatField(default=1e-10, help_text='Enter a number for K11')
    K12 = models.FloatField(default=0, help_text='Enter a number for K12')
    K22 = models.FloatField(default=2e-10, help_text='Enter a number for K22')
    phi = models.FloatField(default=0.5, help_text='Enter a number for volume fraction')
    analysis = models.ForeignKey(Analysis, related_name='preform', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=30)
    preform = models.ForeignKey(Preform, related_name='preform', on_delete=models.SET_NULL, null=True)
    rotate = models.FloatField(default=0, help_text='Degree of rotation')
    analysis = models.ForeignKey(Analysis, related_name='section', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Step(models.Model):
    name = models.CharField(max_length=30)
    typ = models.CharField(max_length=30, choices=TYPE_OF_ANALYSIS, default=0)
    endtime = models.FloatField()
    outputstep = models.FloatField()
    maxiterations = models.IntegerField()
    maxhaltsteps = models.IntegerField()
    minchangesaturation = models.FloatField()
    timescaling = models.FloatField()
    fillthreshold = models.FloatField()
    analysis = models.OneToOneField(Analysis, related_name='step', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class BC(models.Model):
    name = models.CharField(max_length=30)
    typ = models.CharField(max_length=30, choices=TYPE_OF_BC, default=0)
    value = models.FloatField(default=0, help_text='Value on Boundary Condition')
    analysis = models.ForeignKey(Analysis, related_name='bc', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Results(models.Model):
    Step=models.IntegerField(default=0)
    analysis = models.OneToOneField(Analysis, related_name='results', on_delete=models.CASCADE)
