from django import forms
from .models import Analysis
from .models import Mesh
from .models import Material
from .models import Section
from .models import Step
from .models import BC

class NewAnalysisForm(forms.ModelForm):
    class Meta:
        model = Analysis
        fields = ['name', 'description']

class NewMeshForm(forms.ModelForm):
    class Meta:
        model = Mesh
        fields = ['name', 'address']


class NewMaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'typ', 'viscosity', 'permeability']

class NewSectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'material']

    material = forms.ModelChoiceField(queryset = None, initial=0)

    def __init__(self, *args, **kwargs):
        self.analysis = kwargs.pop('analysis')
        super(NewSectionForm, self).__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(analysis=self.analysis)

class NewStepForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = ['name']