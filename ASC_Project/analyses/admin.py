from django.contrib import admin
from .models import Analysis
from .models import Mesh
from .models import Resin
from .models import Preform
from .models import Section
from .models import Step
from .models import BC

admin.site.register(Analysis)
admin.site.register(Mesh)
admin.site.register(Resin)
admin.site.register(Preform)
admin.site.register(Section)
admin.site.register(Step)
admin.site.register(BC)
