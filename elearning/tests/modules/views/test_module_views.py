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
        resp = self.create_content(module=self.public_module.pk)

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


# --- Test Module Views ---


class TestModuleCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("elearning:modules:module-create")
        setup_basic_users_and_module(cls)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def create_module(self, **kwargs):
        response = self.client.post(
            self.url,
            kwargs,
            format="json",
        )
        return response

    def get_module_list(self, **kwargs):
        response = self.client.get(
            self.url,
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.create_module()
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.create_module()
        self.assertEqual(resp.status_code, 403)

    def test_200_happy_path(self):
        resp = self.create_module(
            title="Dark Side of Python", category_id=self.category.pk, is_public=True
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["category"]["id"], self.category.pk)
        self.assertEqual(resp.json()["title"], "Dark Side of Python")
        self.assertEqual(resp.json()["is_public"], True)

    def test_default_category(self):
        resp = self.create_module(title="Dark Side of Python", is_public=True)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["category"]["name"], "Sonstiges")
        self.assertEqual(resp.json()["title"], "Dark Side of Python")
        self.assertEqual(resp.json()["is_public"], True)

    def test_get_module_list(self):
        # private module without user access
        resp = self.create_module(title="Dark Side of Python", is_public=False)
        self.assertEqual(resp.status_code, 201)

        # private module with user access
        resp = self.create_module(title="Python: Forbidden Tactics", is_public=False)
        ModuleAccess.objects.create(
            user=self.normal_user, module=Module.objects.get(id=resp.json()["id"])
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.get_module_list()
        titles = [m["title"] for m in resp.json()]

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(titles), 3)
        self.assertIn("Introduction to Python", titles)
        self.assertIn("Dark Side of Python", titles)
        self.assertIn("Python: Forbidden Tactics", titles)

    def test_title_edge_cases(self):
        resp = self.create_module(category_id=self.category.pk, is_public=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("erforderlich", resp.json()["title"][0])

        resp = self.create_module(
            title="", category_id=self.category.pk, is_public=True
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("nicht leer", resp.json()["title"][0])

        resp = self.create_module(
            title="Viiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiel zu langer Titel",
            category_id=self.category.pk,
            is_public=True,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("200 Zeichen lang", resp.json()["title"][0])

    def test_invalid_category_id(self):
        resp = self.create_module(title="Test", category_id=9999, is_public=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("existiert nicht", resp.json()["category_id"][0])

    def test_duplicates(self):
        resp = self.create_module(
            title="Dark Side of Python", category_id=self.category.pk, is_public=True
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.create_module(
            title="Dark Side of Python", category_id=self.category.pk, is_public=True
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("existiert bereits", resp.json()["title"][0])

    def test_response_structure(self):
        resp = self.create_module(
            title="Dark Side of Python", category_id=self.category.pk, is_public=True
        )
        resp_data = resp.json()
        self.assertEqual(resp_data["chapters"], [])
        self.assertEqual(resp_data["contents"], [])
        self.assertEqual(resp_data["tasks"], [])
        self.assertEqual(resp_data["articles"], [])


class TestModuleUpdateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:module-update"
        setup_basic_users_and_module(cls)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def update_module(self, module_id, **kwargs):
        url = reverse_with_pk(self.view, module_id)
        response = self.client.patch(
            url,
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.update_module(1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.update_module(1)
        self.assertEqual(resp.status_code, 403)

    def test_200_happy_path(self):
        new_category_id = ModuleCategory.objects.create(name="Unethical Python").pk
        resp = self.update_module(
            module_id=self.public_module.pk,
            title="Dark Side of Python",
            category_id=new_category_id,
            is_public=False,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["category"]["id"], new_category_id)
        self.assertEqual(resp.json()["title"], "Dark Side of Python")
        self.assertEqual(resp.json()["is_public"], False)

    def test_title_edge_cases(self):
        resp = self.update_module(module_id=self.public_module.pk, title="")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("nicht leer", resp.json()["title"][0])

        resp = self.update_module(
            module_id=self.public_module.pk,
            title="Viiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            + "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiel zu langer Titel",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("200 Zeichen lang", resp.json()["title"][0])

    def test_invalid_category_id(self):
        resp = self.update_module(module_id=self.public_module.pk, category_id=9999)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("existiert nicht", resp.json()["category_id"][0])

    def test_duplicates(self):
        Module.objects.create(
            title="Dark Side of Python", category=self.category, is_public=False
        )

        resp = self.update_module(
            module_id=self.public_module.pk, title="Dark Side of Python"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("existiert bereits", resp.json()["title"][0])


class TestModuleDetailAdminView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:module-detail-admin"
        setup_basic_users_and_module(cls)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def get_module_details(self, module_id, **kwargs):
        url = reverse_with_pk(self.view, module_id)
        response = self.client.get(
            url,
            kwargs,
            format="json",
        )
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.get_module_details(1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.get_module_details(1)
        self.assertEqual(resp.status_code, 403)

    def test_200_happy_path_big_module(self):
        big_module = Module.objects.create(
            title="Python Komplettkurs",
            category=ModuleCategory.objects.create(name="Python"),
            is_public=True,
        )
        chapter1 = Chapter.objects.create(
            module=big_module,
            title="Kapitel 1 - Einführung",
            description="Python ist...",
        )
        chapter2 = Chapter.objects.create(
            module=big_module,
            title="Kapitel 2 - Was man mit Python alles machen kann",
            description="Folgendes kann man mit Python...",
        )
        content1 = (
            Content.objects.create(
                chapter=chapter1,
                title="Einführung",
                description="Die Einführung in Python...",
                video_url="https://example.com/python/1/intro.mp4",
                supplementary_title="Was Python alles kann",
            ),
        )
        content2 = Content.objects.create(
            chapter=chapter1,
            title="Hinweise",
            description="Allgemeine Hinweise",
        )
        content3 = Content.objects.create(
            chapter=chapter2,
            title="Komplettkurs",
            description="In 100 Stunden lernst du alles, was du über Python wissen musst.",
            video_url="https://example.com/python/2/python_course_100h.mp4",
            supplementary_title="Python in 100 Stunden",
        )
        article1 = Article.objects.create(
            module=big_module,
            title="Python - die Grundlagen",
            url="https://example.com/python-grundlagen",
            json_content={"content": "Beginnen wir mit..."},
        )
        article2 = Article.objects.create(
            module=big_module,
            title="Python - Expertenwissen",
            url="https://example.com/python-expertenwissen",
            json_content={"content": "Weiter geht's mit..."},
        )
        resp = self.get_module_details(big_module.pk)
        print(resp.json())
        self.assertEqual(resp.status_code, 200)
        module = resp.json()

        # module
        self.assertEqual(module["id"], 2)
        self.assertEqual(module["title"], "Python Komplettkurs")
        self.assertEqual(module["category"]["name"], "Python")
        self.assertEqual(module["is_public"], True)

        # chapters
        module["chapters"].sort(key=lambda c: c["id"])
        chapters = module["chapters"]
        self.assertEqual(len(chapters), 2)

        # Kapitel 1 prüfen
        chapter1 = chapters[0]
        self.assertEqual(chapter1["id"], 1)
        self.assertEqual(chapter1["module"], 2)
        self.assertEqual(chapter1["title"], "Kapitel 1 - Einführung")
        self.assertEqual(chapter1["description"], "Python ist...")
        self.assertEqual(chapter1["order"], 0)
        self.assertTrue(chapter1["is_active"])

        # Inhalte von Kapitel 1 prüfen
        chapter1["contents"].sort(key=lambda c: c["id"])
        contents1 = chapter1["contents"]
        self.assertEqual(len(contents1), 2)

        content1 = contents1[0]
        self.assertEqual(content1["id"], 1)
        self.assertEqual(content1["chapter"], 1)
        self.assertEqual(content1["title"], "Einführung")
        self.assertEqual(content1["description"], "Die Einführung in Python...")
        self.assertEqual(
            content1["video_url"], "https://example.com/python/1/intro.mp4"
        )
        self.assertEqual(content1["supplementary_title"], "Was Python alles kann")
        self.assertEqual(content1["order"], 0)
        self.assertEqual(content1["supplementary_contents"], [])

        content2 = contents1[1]
        self.assertEqual(content2["id"], 2)
        self.assertEqual(content2["chapter"], 1)
        self.assertEqual(content2["title"], "Hinweise")
        self.assertEqual(content2["description"], "Allgemeine Hinweise")
        self.assertIsNone(content2["video_url"])
        self.assertIsNone(content2["supplementary_title"])
        self.assertEqual(content2["order"], 0)
        self.assertEqual(content2["supplementary_contents"], [])

        # Kapitel 2 prüfen
        chapter2 = chapters[1]  # Index 1, wenn Kapitel 1 an Index 0 ist
        self.assertEqual(chapter2["id"], 2)
        self.assertEqual(chapter2["module"], 2)
        self.assertEqual(
            chapter2["title"], "Kapitel 2 - Was man mit Python alles machen kann"
        )
        self.assertEqual(chapter2["description"], "Folgendes kann man mit Python...")
        self.assertEqual(chapter2["order"], 0)
        self.assertTrue(chapter2["is_active"])

        # Inhalte von Kapitel 2 prüfen
        contents2 = chapter2["contents"]
        self.assertEqual(len(contents2), 1)  # nur 1 Content erwartet

        content3 = contents2[0]
        self.assertEqual(content3["id"], 3)
        self.assertEqual(content3["chapter"], 2)
        self.assertEqual(content3["title"], "Komplettkurs")
        self.assertEqual(
            content3["description"],
            "In 100 Stunden lernst du alles, was du über Python wissen musst.",
        )
        self.assertEqual(
            content3["video_url"], "https://example.com/python/2/python_course_100h.mp4"
        )
        self.assertEqual(content3["supplementary_title"], "Python in 100 Stunden")
        self.assertEqual(content3["order"], 0)
        self.assertEqual(content3["supplementary_contents"], [])

        # Aggregierte Contents prüfen
        module["contents"].sort(key=lambda c: c["id"])
        content1 = module["contents"][0]
        content2 = module["contents"][1]
        content3 = module["contents"][2]

        self.assertEqual(content1["id"], 1)
        self.assertEqual(content1["chapter"], 1)
        self.assertEqual(content1["title"], "Einführung")
        self.assertEqual(content1["description"], "Die Einführung in Python...")
        self.assertEqual(
            content1["video_url"], "https://example.com/python/1/intro.mp4"
        )

        self.assertEqual(content2["id"], 2)
        self.assertEqual(content2["chapter"], 1)
        self.assertEqual(content2["title"], "Hinweise")
        self.assertEqual(content2["description"], "Allgemeine Hinweise")
        self.assertIsNone(content2["video_url"])

        self.assertEqual(content3["id"], 3)
        self.assertEqual(content3["chapter"], 2)
        self.assertEqual(content3["title"], "Komplettkurs")
        self.assertEqual(
            content3["description"],
            "In 100 Stunden lernst du alles, was du über Python wissen musst.",
        )
        self.assertEqual(
            content3["video_url"], "https://example.com/python/2/python_course_100h.mp4"
        )

        # Aggregierte Articles prüfen
        module["articles"].sort(key=lambda c: c["id"])
        article1 = module["articles"][0]
        article2 = module["articles"][1]

        self.assertEqual(article1["id"], 1)
        self.assertEqual(article1["module"], 2)
        self.assertEqual(article1["title"], "Python - die Grundlagen")
        self.assertEqual(article1["url"], "https://example.com/python-grundlagen")

        self.assertEqual(article2["id"], 2)
        self.assertEqual(article2["module"], 2)
        self.assertEqual(article2["title"], "Python - Expertenwissen")
        self.assertEqual(article2["url"], "https://example.com/python-expertenwissen")


class TestModuleDeleteView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view = "elearning:modules:module-delete"
        setup_basic_users_and_module(cls)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def delete_module(self, module_id):
        url = reverse_with_pk(self.view, module_id)
        response = self.client.delete(url)
        return response

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.delete_module(1)
        self.assertEqual(resp.status_code, 401)

    def test_admin_rights_required(self):
        self.client.force_authenticate(user=self.normal_user)
        resp = self.delete_module(1)
        self.assertEqual(resp.status_code, 403)

    def test_200_happy_path(self):
        resp = self.delete_module(self.public_module.pk)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Module.objects.filter(id=self.public_module.id).exists())

    def test_delete_cascades(self):
        chapter = Chapter.objects.create(module=self.public_module, title="Kapitel 1")
        content = Content.objects.create(chapter=chapter, title="Einführung")
        article = Article.objects.create(
            module=self.public_module, title="Artikel", url="http://example.com"
        )

        resp = self.delete_module(self.public_module.pk)
        self.assertEqual(resp.status_code, 204)

        self.assertFalse(Module.objects.filter(id=self.public_module.id).exists())
        self.assertFalse(Chapter.objects.filter(id=chapter.id).exists())
        self.assertFalse(Content.objects.filter(id=content.id).exists())
        self.assertFalse(Article.objects.filter(id=article.id).exists())
