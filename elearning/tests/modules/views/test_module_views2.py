from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from ....modules.models import (
    Module,
    ModuleCategory,
    Chapter,
    Content,
    SupplementaryContent,
)


class BaseAPITestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_user(
            username="admin", password="password", is_staff=True
        )
        cls.normal_user = User.objects.create_user(
            username="normal_user", password="password"
        )
        cls.category = ModuleCategory.objects.create(name="testcategory")
        cls.module = Module.objects.create(
            title="Module 1", category_id=cls.category.id
        )
        cls.chapter = Chapter.objects.create(
            module=cls.module, order=1, title="Chapter 1"
        )
        cls.content = Content.objects.create(
            chapter=cls.chapter, order=1, title="Content 1"
        )

    def setUp(self):
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "admin", "password": "password"},
        )


class SupplementaryContentCreateViewTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("elearning:modules:supplementary-create")

    def test_unauthenticated(self):
        self.client.cookies.clear()
        response = self.client.post(self.url, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_admin_rights_required(self):
        # sign in as normal user
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "normal_user", "password": "password"},
        )
        response = self.client.post(self.url, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_create_supplementary_content_with_auto_order(self):
        data = {
            "content": self.content.id,
            "label": "descriptive text",
            "url": "http://example.com",
        }
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupplementaryContent.objects.count(), 1)
        obj = SupplementaryContent.objects.first()
        self.assertEqual(obj.order, 1)

        # Add another and check auto increment
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(SupplementaryContent.objects.count(), 2)
        last = SupplementaryContent.objects.order_by("-id").first()
        self.assertEqual(last.order, 2)


class CategoryViewsTest(BaseAPITestCase):
    def test_unauthenticated(self):
        self.client.cookies.clear()

        admin_urls = {
            reverse("elearning:modules:category-list-create"),
            reverse("elearning:modules:category-update", kwargs={"pk": 1}),
        }
        for url in admin_urls:
            response = self.client.post(url, content_type="application/json")
            self.assertEqual(response.status_code, 401)

    def test_admin_rights_required(self):
        # sign in as normal user
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "normal_user", "password": "password"},
        )
        admin_urls = {
            reverse("elearning:modules:category-list-create"),
            reverse("elearning:modules:category-update", kwargs={"pk": 1}),
        }
        for url in admin_urls:
            response = self.client.post(url, content_type="application/json")
            self.assertEqual(response.status_code, 403)

    def test_list_and_create_category(self):
        url = reverse("elearning:modules:category-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = {"name": "Category A"}
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            ModuleCategory.objects.count(), 2
        )  # eine Kategorie in setup erstellt

    def test_update_category(self):
        category = ModuleCategory.objects.create(name="Old")
        url = reverse("elearning:modules:category-update", kwargs={"pk": category.id})
        response = self.client.patch(
            url, {"name": "New"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.name, "New")


class ChapterViewsTest(BaseAPITestCase):
    def setUp(self):
        super().setUp()

    def test_unauthenticated(self):
        self.client.cookies.clear()
        urls = {
            reverse("elearning:modules:chapter-create"),
            reverse("elearning:modules:chapter-update", kwargs={"pk": 1}),
            reverse("elearning:modules:chapter-detail", kwargs={"pk": 1}),
            reverse("elearning:modules:chapter-list"),
            reverse("elearning:modules:chapter-delete", kwargs={"pk": 1}),
        }

        for url in urls:
            response = self.client.post(url, content_type="application/json")
            self.assertEqual(response.status_code, 401)

    def test_admin_rights_required(self):
        # sign in as normal user
        self.client.post(
            reverse("elearning:token_obtain_pair"),
            {"username": "normal_user", "password": "password"},
        )
        admin_urls = {
            reverse("elearning:modules:chapter-create"),
            reverse("elearning:modules:chapter-update", kwargs={"pk": 1}),
            reverse("elearning:modules:chapter-delete", kwargs={"pk": 1}),
        }
        for url in admin_urls:
            response = self.client.post(url, content_type="application/json")
            self.assertEqual(response.status_code, 403)

    def test_create_chapter_auto_order(self):
        url = reverse("elearning:modules:chapter-create")
        data = {"module_id": self.module.id, "title": "Chapter 2"}
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chapter = Chapter.objects.first()
        self.assertEqual(chapter.order, 1)

        # second chapter increments order
        response = self.client.post(
            url,
            {"module": self.module.id, "title": "Chapter 2"},
            content_type="application/json",
        )
        self.assertEqual(Chapter.objects.count(), 2)
        last = Chapter.objects.order_by("-id").first()
        self.assertEqual(last.order, 2)

    def test_update_chapter(self):
        chapter = Chapter.objects.create(module=self.module, order=1, title="Original")
        url = reverse("elearning:modules:chapter-update", kwargs={"pk": chapter.id})
        response = self.client.patch(
            url, {"title": "Updated"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chapter.refresh_from_db()
        self.assertEqual(chapter.title, "Updated")

    def test_detail_chapter(self):
        chapter = Chapter.objects.create(module=self.module, order=1, title="Detail")
        url = reverse("elearning:modules:chapter-detail", kwargs={"pk": chapter.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Detail")

    def test_list_chapters(self):
        Chapter.objects.create(module=self.module, order=1, title="C1")
        Chapter.objects.create(module=self.module, order=2, title="C2")
        url = reverse("elearning:modules:chapter-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 3
        )  # len 3 weil ein Chapter im Setup erstellt wurde

    def test_delete_chapter(self):
        url = reverse(
            "elearning:modules:chapter-delete", kwargs={"pk": self.chapter.id}
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Chapter.objects.count(), 0)

    def test_delete_chapter_no_destroy_order(self):
        Chapter.objects.create(module=self.module, order=2, title="C2")
        url = reverse(
            "elearning:modules:chapter-delete", kwargs={"pk": self.chapter.id}
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        url = reverse("elearning:modules:chapter-create")
        data = {"module_id": self.module.id, "title": "Chapter 2"}
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # TODO: Check nach Korrekter Order der Chapter. Selbe Tests für Category und Supplements.
        # Was ist das intended Verhalten?
