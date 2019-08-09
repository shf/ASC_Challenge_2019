"""ASC_Project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from analyses import views


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.home, name='home'),
    url(r'^(?P<slug>[-\w]+)/mesh/$', views.mesh_page, name='mesh'),
    url(r'^(?P<slug>[-\w]+)/material_submit/$', views.material_page, name='material'),
    url(r'^(?P<slug>[-\w]+)/section_submit/$', views.section_page, name='section'),
    url(r'^(?P<slug>[-\w]+)/step/$', views.step_page, name='step'),
    url(r'^(?P<slug>[-\w]+)/bc/$', views.bc_page, name='bc'),
    url(r'^(?P<slug>[-\w]+)/submit/$', views.submit_page, name='submit'),
    url(r'^(?P<slug>[-\w]+)/result/$', views.result_page, name='result'),
]
