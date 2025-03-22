from django.test import TestCase
from django.urls import reverse
from django.http import HttpResponse
from django.template import Context, Template
from tickets.tests.helpers import MenuTesterMixin


class DummyMenuTest(MenuTesterMixin, TestCase):
    def setUp(self):
        self.menu_urls = [reverse("profile"), reverse("password"), reverse("log_out")]

    def test_one_menu_item_missing(self):
        partial_html = "".join(
            f'<a href="{url}">Link</a>' for url in self.menu_urls[:-1]
        )
        response = HttpResponse(partial_html)
        with self.assertRaises(AssertionError):
            self.assert_menu(response)

    def test_no_menu_items_present(self):
        response = HttpResponse("<html><body><p>No menu</p></body></html>")
        with self.assertRaises(AssertionError):
            self.assert_menu(response)

    def test_all_menu_items_present(self):
        menu_html = "".join(f'<a href="{url}">Link</a>' for url in self.menu_urls)
        response = HttpResponse(menu_html)
        self.assert_menu(response)
