from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from elearning.modules.models import (
    Module,
    ModuleAccess,
    ModuleCategory,
)

User = get_user_model()


def reverse_with_pk(viewname, pk):
    return reverse(viewname, kwargs={"pk": pk})


def setup_basic_users_and_module(cls):
    cls.admin_user = User.objects.create_user(
        username="testuser", password="12345", is_staff=True
    )
    cls.normal_user = User.objects.create_user(username="otto", password="otto12345")
    cls.category = ModuleCategory.objects.create(name="Python Basics")
    cls.public_module = Module.objects.create(
        title="Introduction to Python", category=cls.category, is_public=True
    )


# --- Test Public Views ---


class TestModuleListViewPublic(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("elearning:modules:module-list-public")

    def test_200_empty_list(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_200_test_data(self):
        category = ModuleCategory.objects.create(name="Python Basics")

        public_module = Module.objects.create(
            title="Introduction to Python", category=category, is_public=True
        )

        # private module
        Module.objects.create(
            title="Dark Side of Python", category=category, is_public=False
        )

        # unauthenticated access
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

        returned_module = resp.json()[0]
        self.assertEqual(returned_module["title"], public_module.title)
        self.assertEqual(returned_module["category"]["name"], category.name)


class TestModuleDetailViewPublic(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:module-detail-public"
        cls.category = ModuleCategory.objects.create(name="Python Basics")

    def test_200_test_data(self):
        public_module = Module.objects.create(
            title="Introduction to Python", category=self.category, is_public=True
        )

        # unauthenticated access
        url = reverse_with_pk(self.view, public_module.pk)
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

        returned_module = resp.json()
        self.assertEqual(returned_module["title"], public_module.title)
        self.assertEqual(returned_module["category"]["name"], self.category.name)

    def test_404_no_data(self):
        # unauthenticated access
        url = reverse_with_pk(self.view, 1)
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 404)

    def test_module_is_private(self):
        private_module = Module.objects.create(
            title="Dark Side of Python",
            category=self.category,
            is_public=False,
        )

        # unauthenticated access
        url = reverse_with_pk(self.view, private_module.pk)
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 404)


# --- Test User Module Views ---


class TestUserModuleListView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("elearning:modules:user-module-list")
        setup_basic_users_and_module(cls)
        cls.user2 = User.objects.create_user(username="otto2", password="12345")

        cls.private_module_w_access = Module.objects.create(
            title="Dark Side of Python",
            category=cls.category,
            is_public=False,
        )
        ModuleAccess.objects.create(
            user=cls.normal_user, module=cls.private_module_w_access
        )

        cls.private_module_no_access = Module.objects.create(
            title="Python: Forbidden Tactics",
            category=cls.category,
            is_public=False,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.normal_user)

    def get_user_module_list(self):
        return self.client.get(self.url)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.get_user_module_list()
        self.assertEqual(resp.status_code, 401)

    def test_200_empty_list(self):
        Module.objects.all().delete()
        resp = self.get_user_module_list()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_200_test_data(self):
        resp = self.get_user_module_list()
        module_list = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(module_list), 2)

        modules_by_title = {m["title"]: m for m in module_list}
        module_pub = modules_by_title[self.public_module.title]
        module_priv = modules_by_title[self.private_module_w_access.title]

        self.assertIsNotNone(module_pub)
        self.assertTrue(module_pub["is_public"])
        self.assertEqual(module_pub["category"]["name"], self.category.name)

        self.assertIsNotNone(module_priv)
        self.assertFalse(module_priv["is_public"])
        self.assertEqual(module_priv["category"]["name"], self.category.name)

        titles = [m["title"] for m in module_list]
        self.assertNotIn(self.private_module_no_access.title, titles)

    def test_multiple_users(self):
        self.client.force_authenticate(user=self.user2)
        resp = self.get_user_module_list()

        module_list = resp.json()
        self.assertEqual(len(module_list), 1)

        module = module_list[0]
        self.assertEqual(module["title"], self.public_module.title)
        self.assertTrue(module["is_public"])


class TestUserModuleDetailView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:user-module-detail"
        setup_basic_users_and_module(cls)
        cls.user2 = User.objects.create_user(username="otto2", password="12345")

        cls.private_module_w_access = Module.objects.create(
            title="Dark Side of Python",
            category=cls.category,
            is_public=False,
        )
        ModuleAccess.objects.create(
            user=cls.normal_user, module=cls.private_module_w_access
        )
        cls.private_module_no_access = Module.objects.create(
            title="Python: Forbidden Tactics",
            category=cls.category,
            is_public=False,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.normal_user)

    def get_user_module_detail(self, module_id):
        url = reverse_with_pk(self.view, module_id)
        return self.client.get(url)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.get_user_module_detail(self.private_module_w_access.pk)
        self.assertEqual(resp.status_code, 401)

    def test_404(self):
        resp = self.get_user_module_detail(9999)
        self.assertEqual(resp.status_code, 404)

    def test_200_get_private_module_with_access(self):
        resp = self.get_user_module_detail(self.private_module_w_access.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], self.private_module_w_access.title)

    def test_200_get_private_module_no_access(self):
        resp = self.get_user_module_detail(self.private_module_no_access.pk)
        self.assertEqual(resp.status_code, 403)

    def test_200_get_public_module(self):
        resp = self.get_user_module_detail(self.public_module.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], self.public_module.title)

    def test_multiple_users(self):
        self.client.force_authenticate(user=self.user2)
        resp = self.get_user_module_detail(self.private_module_w_access.pk)
        self.assertEqual(resp.status_code, 403)
