import os

from django.urls import reverse
from django.urls import resolve
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


from .views import home
from .views import mesh_page
from .views import material_page
from .views import section_page
from .views import step_page
from .views import bc_page
from .views import submit_page
from .views import result_page

from .models import Analysis
from .models import Mesh
from .models import Material
from .models import Section

from .forms import NewSectionForm

class HomeTests(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        url = reverse('home')
        self.response = self.client.get(url)

    def test_home_view_status_code(self):
        self.assertEquals(self.response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        view = resolve('/')
        self.assertEquals(view.func, home)

    def test_csrf(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_home_valid_analysis_data(self):
        url = reverse('home')
        self.assertTrue(Analysis.objects.exists())

    def test_home_invalid_analysis_data(self):
        '''
        Invalid analysis data should not redirect
        The expected behavior is to show the form again with validation errors
        '''
        url = reverse('home')
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_home_invalid_analysis_data_empty_fields(self):
        '''
        Invalid analysis data should not redirect
        The expected behavior is to show the form again with validation errors
        '''
        url = reverse('home')
        data = {
            'name': '',
            'discription': ''
        }
        response = self.client.post(url, data)
        self.assertEquals(response.status_code, 200)
        self.assertFalse(Analysis.objects.all().count()==2)

    def test_home_view_contains_create_button(self):
        analysis_url = reverse('home')
        self.assertContains(self.response, 'href="{0}"'.format(analysis_url))

class MeshTests(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')

    def test_mesh_view_status_code(self):
        url = reverse('mesh', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_mesh_view_not_found_status_code(self):
        url = reverse('mesh', kwargs={'slug': 'something'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)    

    def test_mesh_url_resolves_mesh_view(self):
        view = resolve('/test/mesh/')
        self.assertEquals(view.func, mesh_page)

    def test_mesh_valid_mesh_data(self):
        url = reverse('mesh', kwargs={'slug': 'test'})
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")

        data = {
            'name': 'test_mesh',
            'address': mesh
        }

        response = self.client.post(url, data)
        self.assertTrue(Mesh.objects.exists())

        mesh = Mesh.objects.get(name="test_mesh")
        os.remove(mesh.address.path)

    def test_mesh_invalid_mesh_data(self):
        url = reverse('mesh', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_mesh_invalid_mesh_data_empty_fields(self):
        url = reverse('mesh', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'address': ''
        }
        response = self.client.post(url, data)
        self.assertEquals(response.status_code, 200)
        self.assertFalse(Mesh.objects.all())

    def test_mesh_view_contains_create_button(self):
        url = reverse('mesh', kwargs={'slug': 'test'})
        url_material = reverse('material', kwargs={'slug': 'test'})
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")

        data = {
            'name': 'test_mesh',
            'address': mesh
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_material))

        mesh = Mesh.objects.get(name="test_mesh")
        os.remove(mesh.address.path)

class MaterialTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)

    def test_material_view_status_code(self):
        url = reverse('material', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_material_url_resolves_material_view(self):
        view = resolve('/test/material_submit/')
        self.assertEquals(view.func, material_page)

    def test_material_valid_material_data(self):
        url = reverse('material', kwargs={'slug': 'test'})
        data = {
            'name': 'test_material',
            'typ': 0,
            'viscosity': 1000,
            'permeability': 2000,
        }
        response = self.client.post(url, data)
        self.assertTrue(Material.objects.exists())

    def test_material_invalid_material_data(self):
        url = reverse('material', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_material_invalid_material_data_empty_fields(self):
        url = reverse('material', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'typ': '',
            'viscosity': '',
            'permeability': '',

        }
        response = self.client.post(url, data)
        self.assertFalse(Material.objects.exists())

    def test_material_view_contains_create_button(self):
        url = reverse('material', kwargs={'slug': 'test'})
        url_section = reverse('section', kwargs={'slug': 'test'})
        data = {
            'name': 'test_material2',
            'typ': 0,
            'viscosity': 1000,
            'permeability': 2000,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_section))

class SectionTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.material = Material.objects.create(
            id = 1,
            name= 'test_material',
            typ= 0,
            viscosity= 1000,
            permeability= 2000,
            analysis = self.analysis
        )

    def test_section_view_status_code(self):
        url = reverse('section', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_section_url_resolves_section_view(self):
        view = resolve('/test/section_submit/')
        self.assertEquals(view.func, section_page)

    def test_section_valid_section_data(self):
        url = reverse('section', kwargs={'slug': 'test'}) 
        form = NewSectionForm({'name': 'section_test', 'material':1}, analysis=self.analysis)

        self.assertTrue(form.is_valid())

        data = {
            'name': 'section_test2',
            'material':1
        }

        response = self.client.post(url, data)
        self.assertTrue(Section.objects.exists())

    def test_section_invalid_section_data(self):
        url = reverse('section', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_section_invalid_section_data_empty_fields(self):
        url = reverse('section', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'material': '',

        }
        response = self.client.post(url, data)
        self.assertFalse(Section.objects.exists())

    def test_section_view_contains_create_button(self):
        url = reverse('section', kwargs={'slug': 'test'})
        url_section = reverse('step', kwargs={'slug': 'test'})
        data = {
            'name': 'section_test',
            'material':1
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_section))

class StepTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.material = Material.objects.create(
            id = 1,
            name= 'test_material',
            typ= 0,
            viscosity= 1000,
            permeability= 2000,
            analysis = self.analysis,
        )
        self.section = Section.objects.create(
            id = 1,
            name = 'section_test',
            material=self.material,
            analysis = self.analysis,
        )

    def test_step_view_status_code(self):
        url = reverse('step', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_step_url_resolves_step_view(self):
        view = resolve('/test/step/')
        self.assertEquals(view.func, step_page)

class BCTest(TestCase):
    def setUp(self):
        Analysis.objects.create(name='test', description='Test analysis.')

    def test_bc_view_status_code(self):
        url = reverse('bc', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_bc_url_resolves_bc_view(self):
        view = resolve('/test/bc/')
        self.assertEquals(view.func, bc_page)

class SubmitTest(TestCase):
    def setUp(self):
        Analysis.objects.create(name='test', description='Test analysis.')

    def test_submit_view_status_code(self):
        url = reverse('submit', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_submit_url_resolves_submit_view(self):
        view = resolve('/test/submit/')
        self.assertEquals(view.func, submit_page)

class ResultTest(TestCase):
    def setUp(self):
        Analysis.objects.create(name='test', description='Test analysis.')

    def test_result_view_status_code(self):
        url = reverse('result', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_result_url_resolves_result_view(self):
        view = resolve('/test/result/')
        self.assertEquals(view.func, result_page)