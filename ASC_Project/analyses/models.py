from django.db import models
from django.contrib.auth.models import User

from .choice import TYPE_OF_ANALYSIS
from .choice import TYPE_OF_BC


class Analysis(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of analysis')
    description = models.CharField(max_length=200, help_text='Description')

    def __str__(self):
        return self.name

class Mesh(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of mesh')
    analysis = models.OneToOneField(Analysis, related_name='mesh', on_delete=models.CASCADE)
    address = models.FileField(upload_to='meshfiles/')

    def __str__(self):
        return self.name

class Resin(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of Resin')
    viscosity = models.FloatField(default=0.02, help_text='Enter a number for viscosity')
    analysis = models.OneToOneField(Analysis, related_name='resin', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Preform(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of Preform')
    thickness = models.FloatField(default=0.01, help_text='Thickness')
    K11 = models.FloatField(default=1e-10, help_text='Enter a number for K11')
    K12 = models.FloatField(default=0, help_text='Enter a number for K12')
    K22 = models.FloatField(default=2e-10, help_text='Enter a number for K22')
    analysis = models.ForeignKey(Analysis, related_name='preform', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=30, unique=True)
    preform = models.ForeignKey(Preform, related_name='preform', on_delete=models.SET_NULL, null=True)
    rotate = models.FloatField(default=0, help_text='Degree of rotation')
    analysis = models.ForeignKey(Analysis, related_name='section', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Step(models.Model):
    name = models.CharField(max_length=30, unique=True)
    typ = models.IntegerField(choices=TYPE_OF_ANALYSIS, default=0)
    endtime = models.FloatField(default=0, help_text='Time to end analysis')
    analysis = models.OneToOneField(Analysis, related_name='step', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class BC(models.Model):
    name = models.CharField(max_length=30, unique=True)
    typ = models.IntegerField(choices=TYPE_OF_BC, default=0)
    value = models.FloatField(default=0, help_text='Value on Boundary Condition')
    analysis = models.ForeignKey(Analysis, related_name='bc', on_delete=models.CASCADE)

    def __str__(self):
        return self.name