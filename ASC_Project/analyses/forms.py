from django import forms
from .models import Analysis
from .models import Mesh
from .models import Resin
from .models import Preform
from .models import Section
from .models import Step
from .models import BC

from .choice import TYPE_OF_ANALYSIS
from .choice import TYPE_OF_BC


class NewAnalysisForm(forms.ModelForm):
    class Meta:
        model = Analysis
        fields = ['name', 'description']

class NewMeshForm(forms.ModelForm):
    class Meta:
        model = Mesh
        fields = ['address']

class MeshConfirmationForm(forms.Form):
    CHOICES=[('yes','Yes'),
         ('no','No')]
    like = forms.CharField(label= 'Do you confirm the mesh?', 
        widget=forms.RadioSelect(choices=CHOICES))


class NewResinForm(forms.ModelForm):
    class Meta:
        model = Resin
        fields = ['name', 'viscosity']

class NewPreformForm(forms.ModelForm):
    btn = forms.CharField(label='', widget=forms.HiddenInput())
    class Meta:
        model = Preform
        fields = ['name', 'thickness', 'K11', 'K12', 'K22']

class NewSectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'preform', 'rotate']

    preform = forms.ModelChoiceField(queryset = None, initial=0)

    def __init__(self, *args, **kwargs):
        self.analysis = kwargs.pop('analysis')
        super(NewSectionForm, self).__init__(*args, **kwargs)
        self.fields['preform'].queryset = Preform.objects.filter(analysis=self.analysis)

class NewStepForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = ['name', 'typ', 'endtime']
    
    typ = forms.ChoiceField(choices = TYPE_OF_ANALYSIS)

class NewBCForm(forms.ModelForm):
    class Meta:
        model = BC
        fields = ['name', 'typ', 'value']
    
    typ = forms.ChoiceField(choices = TYPE_OF_BC)



