import os

from django.urls import reverse
from django.urls import resolve
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


from .views import home
from .views import mesh_page
from .views import resin_page
from .views import preform_page
from .views import section_page
from .views import step_page
from .views import bc_page
from .views import submit_page
from .views import result_page

from .models import Analysis
from .models import Mesh
from .models import Nodes
from .models import Connectivity
from .models import Resin
from .models import Preform
from .models import Section
from .models import Step
from .models import BC

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
        
        with open("analyses/TestData/TestMesh.unv") as fp:
            self.client.post(url, {'analysis_id': Analysis.id, 'address':fp})

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
        url_resin = reverse('resin', kwargs={'slug': 'test'})
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")

        data = {
            'name': 'test_mesh',
            'address': mesh
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_resin))

        mesh = Mesh.objects.get(name="test_mesh")
        os.remove(mesh.address.path)

class MeshDisplayTests(TestCase):
    pass

class ResinTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)

    def test_resin_view_status_code(self):
        url = reverse('resin', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_resin_url_resolves_resin_view(self):
        view = resolve('/test/resin/')
        self.assertEquals(view.func, resin_page)

    def test_resin_valid_resin_data(self):
        url = reverse('resin', kwargs={'slug': 'test'})
        data = {
            'name': 'test_resin',
            'viscosity': 1000,
        }
        response = self.client.post(url, data)
        self.assertTrue(Resin.objects.exists())

    def test_resin_invalid_resin_data(self):
        url = reverse('resin', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_resin_invalid_resin_data_empty_fields(self):
        url = reverse('resin', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'viscosity': '',
        }
        response = self.client.post(url, data)
        self.assertFalse(Resin.objects.exists())

    def test_resin_view_contains_create_button(self):
        url = reverse('resin', kwargs={'slug': 'test'})
        url_preform = reverse('preform', kwargs={'slug': 'test'})
        data = {
            'name': 'test_resin2',
            'viscosity': 1000,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_preform))

class PreformTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        self.resin = Resin.objects.create(name='test_resin', viscosity= 1000, analysis=self.analysis)
        os.remove(self.mesh.address.path)

    def test_preform_view_status_code(self):
        url = reverse('preform', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_preform_url_resolves_preform_view(self):
        view = resolve('/test/preform/')
        self.assertEquals(view.func, preform_page)

    def test_preform_valid_preform_data(self):
        url = reverse('preform', kwargs={'slug': 'test'})
        data = {
            'name': 'test_preform',
            'thickness': 0.1,
            'K11': 1e-9,
            'K12': 0.0,
            'K22': 1e-8,
        }
        response = self.client.post(url, data)
        self.assertTrue(Preform.objects.exists())

    def test_preform_invalid_preform_data(self):
        url = reverse('preform', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_preform_invalid_preform_data_empty_fields(self):
        url = reverse('preform', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'thickness': '',
            'K11': '',
            'K12': '',
            'K22': '',
        }
        response = self.client.post(url, data)
        self.assertFalse(Preform.objects.exists())

    def test_preform_view_contains_create_button(self):
        url = reverse('preform', kwargs={'slug': 'test'})
        url_section = reverse('section', kwargs={'slug': 'test'})
        data = {
            'name': 'test_preform2',
            'thickness': 0.1,
            'K11': 1e-9,
            'K12': 0.0,
            'K22': 1e-8,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_section))

class SectionTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.resin = Resin.objects.create(
            id = 1,
            name= 'test_resin',
            viscosity= 1000,
            analysis = self.analysis,
        )
        self.preform = Preform.objects.create(
            id = 1,
            name = 'test_preform',
            thickness = 1.0,
            K11 = 1e-10,
            K12 = 0.0,
            K22 = 2e-10,
            analysis = self.analysis,
        )

    def test_section_view_status_code(self):
        url = reverse('section', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_section_url_resolves_section_view(self):
        view = resolve('/test/section/')
        self.assertEquals(view.func, section_page)

    def test_section_valid_section_data(self):
        url = reverse('section', kwargs={'slug': 'test'}) 
        form = NewSectionForm({'name': 'section_test', 'preform':1, 'rotate':45}, analysis=self.analysis)

        self.assertTrue(form.is_valid())

        data = {
            'name': 'section_test',
            'preform':1,
            'rotate':45,
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
            'preform': '',
            'rotate': '',
        }
        response = self.client.post(url, data)
        self.assertFalse(Section.objects.exists())

    def test_section_view_contains_create_button(self):
        url = reverse('section', kwargs={'slug': 'test'})
        url_step = reverse('step', kwargs={'slug': 'test'})
        data = {
            'name': 'section_test2',
            'preform': 1,
            'rotate': 45,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_step))

class StepTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.resin = Resin.objects.create(
            id = 1,
            name= 'test_resin',
            viscosity= 1000,
            analysis = self.analysis,
        )
        self.preform = Preform.objects.create(
            id = 1,
            name= 'test_preform',
            thickness = 0.1,
            K11 = 1e-10,
            K12 = 0.0,
            K22 = 2e-10,
            analysis = self.analysis,
        )
        self.section = Section.objects.create(
            id = 1,
            name = 'section_test',
            preform=self.preform,
            rotate = 45,
            analysis = self.analysis,
        )

    def test_step_view_status_code(self):
        url = reverse('step', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_step_url_resolves_step_view(self):
        view = resolve('/test/step/')
        self.assertEquals(view.func, step_page)

    def test_step_valid_step_data(self):
        url = reverse('step', kwargs={'slug': 'test'}) 
        data = {
            'name': 'step_test',
            'typ':0,
            'endtime':100,
        }

        response = self.client.post(url, data)
        self.assertTrue(Step.objects.exists())

    def test_step_invalid_step_data(self):
        url = reverse('step', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_step_invalid_step_data_empty_fields(self):
        url = reverse('step', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'typ': '',
            'endtime': '',
        }
        response = self.client.post(url, data)
        self.assertFalse(Step.objects.exists())

    def test_step_view_contains_create_button(self):
        url = reverse('step', kwargs={'slug': 'test'})
        url_bc = reverse('bc', kwargs={'slug': 'test'})
        data = {
            'name': 'step_test2',
            'typ': 1,
            'endtime': 200,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_bc))

class BCTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.resin = Resin.objects.create(
            id = 1,
            name= 'test_resin',
            viscosity= 1000,
            analysis = self.analysis,
        )
        self.preform = Preform.objects.create(
            id = 1,
            name= 'test_preform',
            thickness = 0.1,
            K11 = 1e-10,
            K12 = 0.0,
            K22 = 2e-10,
            analysis = self.analysis,
        )
        self.section = Section.objects.create(
            id = 1,
            name = 'section_test',
            preform=self.preform,
            rotate = 45,
            analysis = self.analysis,
        )
        self.step = Step.objects.create(
            id = 1,
            name = 'step_test',
            typ = 1,
            endtime = 200,
            analysis = self.analysis,
        )

    def test_bc_view_status_code(self):
        url = reverse('bc', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_bc_url_resolves_bc_view(self):
        view = resolve('/test/bc/')
        self.assertEquals(view.func, bc_page)

    def test_bc_valid_step_data(self):
        url = reverse('bc', kwargs={'slug': 'test'}) 
        data = {
            'name': 'bc_test',
            'typ':0,
            'value':100000,
        }

        response = self.client.post(url, data)
        self.assertTrue(BC.objects.exists())

    def test_step_invalid_step_data(self):
        url = reverse('bc', kwargs={'slug': 'test'})
        response = self.client.post(url, {})
        self.assertEquals(response.status_code, 200)

    def test_step_invalid_step_data_empty_fields(self):
        url = reverse('bc', kwargs={'slug': 'test'})
        data = {
            'name': '',
            'typ': '',
            'value': '',
        }
        response = self.client.post(url, data)
        self.assertFalse(BC.objects.exists())

    def test_step_view_contains_create_button(self):
        url = reverse('bc', kwargs={'slug': 'test'})
        url_submit = reverse('submit', kwargs={'slug': 'test'})
        data = {
            'name': 'bc_test2',
            'typ': 1,
            'value': 200,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '{0}'.format(url_submit))

class SubmitTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')
        mesh = SimpleUploadedFile("mesh.xml", b"file_content", content_type="mesh/xml")
        self.mesh = Mesh.objects.create(name='mesh_test', address=mesh, analysis=self.analysis)
        os.remove(self.mesh.address.path)
        self.resin = Resin.objects.create(
            id = 1,
            name= 'test_resin',
            viscosity= 1000,
            analysis = self.analysis,
        )
        self.preform = Preform.objects.create(
            id = 1,
            name= 'test_preform',
            thickness = 0.1,
            K11 = 1e-10,
            K12 = 0.0,
            K22 = 2e-10,
            analysis = self.analysis,
        )
        self.section = Section.objects.create(
            id = 1,
            name = 'section_test',
            preform=self.preform,
            rotate = 45,
            analysis = self.analysis,
        )
        self.step = Step.objects.create(
            id = 1,
            name = 'step_test',
            typ = 1,
            endtime = 200,
            analysis = self.analysis,
        )
        self.bc = BC.objects.create(
            id = 1,
            name = 'bc_test',
            typ = 1,
            value = 100,
            analysis = self.analysis,
        )

    def test_submit_view_status_code(self):
        url = reverse('submit', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_submit_url_resolves_submit_view(self):
        view = resolve('/test/submit/')
        self.assertEquals(view.func, submit_page)

class ResultTest(TestCase):
    def setUp(self):
        self.analysis = Analysis.objects.create(name='test', description='Test analysis.')

    def test_result_view_status_code(self):
        url = reverse('result', kwargs={'slug': 'test'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_result_url_resolves_result_view(self):
        view = resolve('/test/result/')
        self.assertEquals(view.func, result_page)
