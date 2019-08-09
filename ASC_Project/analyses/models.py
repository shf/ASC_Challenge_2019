from django.db import models
from django.contrib.auth.models import User

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

class Material(models.Model):
    name = models.CharField(max_length=30, unique=True, help_text='Name of material')
    typ = models.PositiveSmallIntegerField(default=0, help_text='Type of material, 0 for default')
    viscosity = models.FloatField(default=0, help_text='Enter a number for viscosity')
    permeability = models.FloatField(default=0, help_text='Enter a number for permeability')
    analysis = models.ForeignKey(Analysis, related_name='material', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Section(models.Model):
    name = models.CharField(max_length=30, unique=True)
#   region={}

    material = models.ForeignKey(Material, related_name='material', on_delete=models.SET_NULL, null=True)
    analysis = models.ForeignKey(Analysis, related_name='section', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Step(models.Model):
    name = models.CharField(max_length=30, unique=True)
    analysis = models.ForeignKey(Analysis, related_name='step', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class BC(models.Model):
    name = models.CharField(max_length=30, unique=True)
    typ = models.PositiveSmallIntegerField(default=0)
    region = {}

    def __str__(self):
        return self.name