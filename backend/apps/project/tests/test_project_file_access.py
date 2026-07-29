from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.project.models import Project, ProjectFile
from apps.project.views import _user_can_access_project_file

User = get_user_model()


class ProjectFileAccessTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_pf@example.com", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_pf@example.com",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        self.operator = User.objects.create_user(
            email="operator_pf@example.com",
            password="pass12345",
            role="operator",
            is_active=True,
            is_staff=True,
        )
        self.sales = User.objects.create_user(
            email="sales_pf@example.com",
            password="pass12345",
            role="sales",
            is_active=True,
            is_staff=True,
        )
        self.stranger = User.objects.create_user(
            email="stranger_pf@example.com", password="pass12345", role="member", is_active=True
        )
        self.project = Project.objects.create(
            project_no=Project.generate_no(),
            title="PF Access Test",
            buyer=self.buyer,
            supplier=self.supplier,
        )
        self.pf = ProjectFile.objects.create(
            project=self.project,
            uploader=self.supplier,
            file=SimpleUploadedFile("spec.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            file_name="spec.pdf",
            file_category="design",
            visibility="all",
        )
        self.pf_internal = ProjectFile.objects.create(
            project=self.project,
            uploader=self.supplier,
            file=SimpleUploadedFile("internal.pdf", b"%PDF-1.4 internal", content_type="application/pdf"),
            file_name="internal.pdf",
            file_category="other",
            visibility="internal",
        )

    def test_admin_roles_can_access(self):
        self.assertTrue(_user_can_access_project_file(self.operator, self.project, self.pf))
        self.assertTrue(_user_can_access_project_file(self.sales, self.project, self.pf_internal))

    def test_legacy_admin_string_denied(self):
        legacy = SimpleNamespace(role="admin", id=-1)
        self.assertFalse(_user_can_access_project_file(legacy, self.project, self.pf))

    def test_buyer_visibility(self):
        self.assertTrue(_user_can_access_project_file(self.buyer, self.project, self.pf))
        self.assertFalse(_user_can_access_project_file(self.buyer, self.project, self.pf_internal))

    def test_supplier_and_stranger(self):
        self.assertTrue(_user_can_access_project_file(self.supplier, self.project, self.pf_internal))
        self.assertFalse(_user_can_access_project_file(self.stranger, self.project, self.pf))
