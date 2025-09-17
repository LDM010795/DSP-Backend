from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from elearning.modules.models import (
    Article,
    Chapter,
    Content,
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


# --- Test Article Views ---


class TestArticleCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("elearning:modules:article-create")
        setup_basic_users_and_module(cls)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def create_article(self, **kwargs):
        response = self.client.post(
            self.url,
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.create_article(module_id=1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(self.normal_user)
        resp = self.create_article(module_id=1)
        self.assertEqual(resp.status_code, 403)

    def test_module_doesnt_exist(self):
        resp = self.create_article(module_id=999)

        self.assertEqual(resp.status_code, 400)
        self.assertIn("existiert nicht", resp.json()["module_id"][0])

    def test_200_happy_path(self):
        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python?",
            url="https://example.com/artikel",
        )
        self.assertEqual(resp.status_code, 201)

    def test_400_article_title_duplicate(self):
        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python?",
            url="https://example.com/artikel",
        )
        self.assertEqual(resp.status_code, 201)

        # again, same article with same title
        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python?",
            url="https://example.com/artikel2",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("title", resp.json()["non_field_errors"][0])

    def test_order_increasing(self):
        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python?",
            url="https://example.com/artikel",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["order"], 1)

        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python good for?",
            url="https://example.com/artikel2",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["order"], 2)

    def test_mandatory_fields(self):
        resp = self.create_article(json_content={"content": "Python is..."})

        self.assertEqual(resp.status_code, 400)
        self.assertIn("Dieses Feld ist erforderlich.", resp.json()["title"])
        self.assertIn("Dieses Feld ist erforderlich.", resp.json()["url"])
        # evtl kommt noch Prüfung auf "module_id" dazu, DB-Struktur steht noch nicht ganz

    def test_valid_urls(self):
        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python?",
            url="https://example.com/artikel",
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python good for?",
            url="http://example.com/artikel#Kapitel2",
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python really good for?",
            url="https://subdomain.example.com",
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python exceptionally good for?",
            url="https://example.com/articles/123/",
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.create_article(
            module_id=self.public_module.pk,
            title="What is Python astronomically good for?",
            url="https://example.com/article we need spaces in the path",
        )
        self.assertEqual(resp.status_code, 201)

    """ #TODO: Unsere Custom URL-Validierung verbessern, dass diese Fehler richtig erkannt werden
    def test_invalid_urls(self):
        resp = self.send_post(module_id=self.public_module.pk, url="https://example!.com/artikel")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ValidationError", resp.json())

        resp = self.send_post(module_id=self.public_module.pk, url="htps://example.com/artikel")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ValidationError", resp.json())

        resp = self.send_post(module_id=self.public_module.pk, url="https:///example.com/artikel")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ValidationError", resp.json())

        resp = self.send_post(module_id=self.public_module.pk, url="example,com/artikel")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ValidationError", resp.json())
    """


class TestArticleUpdateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:article-update"
        setup_basic_users_and_module(cls)
        cls.article = Article.objects.create(
            module=cls.public_module,
            title="What is Python?",
            url="https://example.com/artikel",
            json_content={"content": "Python is..."},
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def update_article(self, pk, **kwargs):
        response = self.client.patch(
            reverse_with_pk(self.view, pk),
            kwargs,
            format="json",
        )
        return response

    def delete_article(self, pk):
        return self.client.delete(reverse_with_pk(self.view, pk))

    def get_article(self, pk):
        return self.client.get(reverse_with_pk(self.view, pk))

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.update_article(pk=1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.update_article(pk=1)
        self.assertEqual(resp.status_code, 403)

    def test_happy_path_update(self):
        resp = self.update_article(
            pk=self.article.pk,
            url="https://example.com/article_update",
            title="What is Python good for?",
            json_content={"content": "Python is good for..."},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["module"], self.public_module.pk)
        self.assertEqual(resp.json()["title"], "What is Python good for?")
        self.assertEqual(resp.json()["url"], "https://example.com/article_update")
        self.assertEqual(
            resp.json()["json_content"], {"content": "Python is good for..."}
        )

    def test_title_update_conflict(self):
        Article.objects.create(  # add a second article
            module=self.public_module,
            title="What is Python good for?",
            url="https://example.com/artikel",
            json_content={"content": "Python is..."},
        )

        # Try to change the first article's title
        resp = self.update_article(pk=self.article.pk, title="What is Python good for?")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("title", resp.json()["non_field_errors"][0])

    def test_delete_article(self):
        resp = self.delete_article(pk=self.article.pk)
        self.assertEqual(resp.status_code, 204)

    def test_delete_nonexisting_article(self):
        resp = self.delete_article(pk=2)
        self.assertEqual(resp.status_code, 404)

    def test_get_article(self):
        resp = self.get_article(pk=self.article.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.public_module.pk, resp.json()["module"])
        self.assertEqual(self.article.title, resp.json()["title"])
        self.assertEqual(self.article.url, resp.json()["url"])
        self.assertEqual(self.article.json_content, resp.json()["json_content"])

    def test_get_nonexisting_article(self):
        resp = self.get_article(pk=2)
        self.assertEqual(resp.status_code, 404)


# --- Test Content Views ---


class TestContentCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("elearning:modules:content-create")
        setup_basic_users_and_module(cls)
        cls.chapter = Chapter.objects.create(
            title="Kapitel 1",
            module=cls.public_module,
            description="Python Basics - Introduction",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def create_content(self, **kwargs):
        response = self.client.post(
            self.url,
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.create_content(module_id=1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.create_content(module_id=1)
        self.assertEqual(resp.status_code, 403)

    def test_200_happy_path(self):
        resp = self.create_content(
            module=self.public_module.pk,
            chapter=self.chapter.pk,
            title="Intro",
            video_url="https://example.com/artikel_1/intro.mp4",
            supplementary_title="Was Python alles kann",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["chapter"], self.chapter.pk)
        self.assertEqual(resp.json()["title"], "Intro")
        self.assertEqual(resp.json()["supplementary_title"], "Was Python alles kann")
        self.assertEqual(
            resp.json()["video_url"], "https://example.com/artikel_1/intro.mp4"
        )

    def test_title_from_video_url(self):
        resp = self.create_content(
            module=self.public_module.pk,
            chapter=self.chapter.pk,
            video_url="https://example.com/artikel_1/intro.mp4",
        )

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "intro")
        self.assertEqual(
            resp.json()["video_url"], "https://example.com/artikel_1/intro.mp4"
        )

    def test_order_increasing(self):
        resp = self.create_content(
            module=self.public_module.pk, chapter=self.chapter.pk, title="Intro"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["order"], 1)

        resp = self.create_content(
            module=self.public_module.pk, chapter=self.chapter.pk, title="Hello World"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["order"], 2)

        resp = self.create_content(
            module=self.public_module.pk,
            chapter=Chapter.objects.create(
                title="Kapitel 2",
                module=self.public_module,
                description="Python Basics - Methods",
            ).pk,
            title="Intro 2",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["order"], 1)

    def test_mandatory_fields(self):
        # title and chapter missing
        resp = self.create_content(
            module=self.public_module.pk
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("Dieses Feld ist erforderlich.", resp.json()["chapter"])
        self.assertIn("Dieses Feld ist erforderlich.", resp.json()["title"])


class TestContentUpdateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:content-update"
        setup_basic_users_and_module(cls)
        cls.chapter = Chapter.objects.create(
            title="Kapitel 1",
            module=cls.public_module,
            description="Python Basics - Introduction",
        )
        cls.content = Content.objects.create(
            chapter=cls.chapter,
            title="Intro",
            video_url="https://example.com/artikel_1/intro.mp4",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def update_content(self, pk, **kwargs):
        response = self.client.patch(
            reverse_with_pk(self.view, pk),
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.update_content(pk=1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.update_content(pk=1)
        self.assertEqual(resp.status_code, 403)

    def test_happy_path_update(self):
        resp = self.update_content(
            pk=self.content.pk,
            chapter=self.chapter.pk,
            title="What is Python good for?",
            video_url="https://example.com/artikel_1/intro.mp4",
            description="Python is good for...",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["chapter"], self.chapter.pk)
        self.assertEqual(resp.json()["title"], "What is Python good for?")
        self.assertEqual(
            resp.json()["video_url"], "https://example.com/artikel_1/intro.mp4"
        )
        self.assertEqual(resp.json()["description"], "Python is good for...")

    def test_title_update_conflict(self):
        Content.objects.create(  # add a second content
            chapter=self.chapter,
            title="Python - Functions",
            video_url="https://example.com/python_functions.mp4",
            description="Python functions are...",
        )

        # Try to change the first contents's title
        resp = self.update_content(pk=self.content.pk, title="Python - Functions")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("title", resp.json()["non_field_errors"][0])