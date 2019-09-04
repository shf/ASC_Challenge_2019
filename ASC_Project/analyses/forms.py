from django import forms
from .models import Analysis
from .models import Mesh
from .models import Nodes
from .models import Resin
from .models import Preform
from .models import Section
from .models import Step
from .models import BC

from .choice import TYPE_OF_ANALYSIS
from .choice import TYPE_OF_BC
from .choice import CONDITION_OF_BC
from .choice import BINARY_CHOICES

class NewAnalysisForm(forms.ModelForm):
    class Meta:
        model = Analysis
        fields = ['name', 'description']

class NewMeshForm(forms.ModelForm):
    class Meta:
        model = Mesh
        fields = ['address']

class MeshConfirmationForm(forms.Form):
    like = forms.CharField(label= 'Do you confirm the mesh?', 
        widget=forms.RadioSelect(choices=BINARY_CHOICES))


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
    name = forms.ChoiceField(label='Face',choices = ())
    preform = forms.ModelChoiceField(queryset = None, initial=0)
    btn = forms.CharField(label='', widget=forms.HiddenInput())
    def __init__(self, *args, **kwargs):
        self.analysis = kwargs.pop('analysis')
        self.mesh = kwargs.pop('mesh')
        super(NewSectionForm, self).__init__(*args, **kwargs)
        self.fields['preform'].queryset = Preform.objects.filter(analysis=self.analysis)
        FaceList=["_None"]
        for items in Nodes.objects.filter(mesh_id=self.mesh).values():
            if items['FaceGroup'] not in FaceList:
                FaceList.append(items['FaceGroup'])
        FaceList.remove("_None")
        _choices=[]
        for i in range(len(FaceList)):
            _choices.append((FaceList[i],FaceList[i]))
        self.fields['name'].choices = tuple(_choices)

class NewStepForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = ['name', 'typ', 'endtime', 'outputstep', 'maxiterations', 'maxhaltsteps', 'minchangesaturation', 'minchangesaturation', 'timescaling', 'fillthreshold']
    
    typ = forms.ChoiceField(label='Termination type', choices=TYPE_OF_ANALYSIS, help_text='The analysis might terminate with unfilled region if you choose "Fill the outlet"')
    endtime = forms.FloatField(label='End time', initial='1000', help_text='End time of analysis')
    outputstep = forms.FloatField(label='Output time step', initial='0.01', help_text='Step size for writing output')
    maxiterations = forms.IntegerField(label='Maximum iteration number', initial='10000', help_text='Maximum number of iterations')
    maxhaltsteps = forms.IntegerField(label='Maximum idle iterations', initial='10', help_text='Maximum number of consequtive steps with no apparant change in saturation')
    minchangesaturation = forms.FloatField(label='Minimum saturation change', initial='0.001', help_text='Minimum acceptable change of saturation')
    timescaling = forms.FloatField(label='Time scaling factor', initial='5.0', help_text='Parameter to scale predicted filling time')
    fillthreshold = forms.FloatField(label='Filling threshhold', initial='0.98', help_text='Threshold for counting filled CVs')


class NewBCForm(forms.ModelForm):
    class Meta:
        model = BC
        fields = ['name', 'typ', 'condition', 'value']

    typ = forms.ChoiceField(label='Boundary Type', choices = TYPE_OF_BC)
    condition = forms.ChoiceField(label='How to enforce', choices = CONDITION_OF_BC, help_text='''The inlet boundary can be described using pressure or flow-rate.
        The outlet can just accept pressure. For walls choose None.''')
    name = forms.ChoiceField(label='Edge',choices = ())
    btn = forms.CharField(label='', widget=forms.HiddenInput())
    def __init__(self, *args, **kwargs):
        self.mesh = kwargs.pop('mesh')
        super(NewBCForm, self).__init__(*args, **kwargs)
        EdgeList=["_None"]
        for items in Nodes.objects.filter(mesh_id=self.mesh).values():
            if items['EdgeGroup'] not in EdgeList:
                EdgeList.append(items['EdgeGroup'])
        EdgeList.remove("_None")
        _choices=[]
        for i in range(len(EdgeList)):
            _choices.append((EdgeList[i],EdgeList[i]))
        self.fields['name'].choices = tuple(_choices)

    
class JobSubmitForm(forms.Form):
    btn = forms.CharField(label='', widget=forms.HiddenInput())

class StatusForm(forms.Form):
    btn = forms.CharField(label='', widget=forms.HiddenInput())
    
class ResultsForm(forms.Form):
    btn = forms.CharField(label='', widget=forms.HiddenInput())
