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

from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path
from django.conf.urls import url
from django.conf import settings

from analyses import views


urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('<slug:slug>/mesh/', views.mesh_page, name='mesh'),
    path('<slug:slug>/mesh/<int:pk>', views.display_mesh, name='meshdisplay'),
    path('<slug:slug>/resin/', views.resin_page, name='resin'),
    path('<slug:slug>/preform/', views.preform_page, name='preform'),
    path('<slug:slug>/section/', views.section_page, name='section'),
    path('<slug:slug>/step/', views.step_page, name='step'),
    path('<slug:slug>/bc/', views.bc_page, name='bc'),
    path('<slug:slug>/submit/', views.submit_page, name='submit'),
    path('<slug:slug>/result/', views.result_page, name='result'),
    path('<slug:slug>/result_old/', views.result_old_page, name='result_old'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

