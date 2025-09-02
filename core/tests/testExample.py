from django.test import TestCase

# Create your tests here.


class TestTestCase(TestCase):
    def setUp(self):
        print("This is a setup phase! Create mock data here")

    def test_feature_to_test(self):
        print("Feature getting tested!")
        self.assertTrue(True)

    def tearDown(self):
        print("This is a teardown phase! If stuff needs to be killed, do it here")
