import unittest

from app import app


class HomeEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_returns_http_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_home_returns_expected_body(self):
        response = self.client.get("/")
        self.assertEqual(
            response.get_data(as_text=True),
            "Hello, Jenkins Multi-Stage Pipeline!",
        )

    def test_unknown_route_returns_404(self):
        response = self.client.get("/missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
