import unittest

from app import greet


class GreetTests(unittest.TestCase):
    def test_greets_a_name(self):
        self.assertEqual(greet("Anshika"), "Hello, Anshika!")

    def test_uses_default_name(self):
        self.assertEqual(greet(), "Hello, World!")

    def test_trims_surrounding_whitespace(self):
        self.assertEqual(greet("  Jenkins  "), "Hello, Jenkins!")

    def test_rejects_an_empty_name(self):
        with self.assertRaises(ValueError):
            greet("   ")

    def test_rejects_a_non_string_name(self):
        with self.assertRaises(TypeError):
            greet(42)


if __name__ == "__main__":
    unittest.main()
