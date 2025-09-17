from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from elearning.modules.models import (
    Module,
    ModuleCategory,
)

User = get_user_model()


def reverse_with_pk(viewname, pk):
    return reverse(viewname, kwargs={"pk": pk})


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
