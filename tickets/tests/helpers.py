from django.urls import reverse
from with_asserts.mixin import AssertHTMLMixin

def reverse_with_next(url_name, next_url):
    """Extended version of reverse to generate URLs with redirects"""
    url = reverse(url_name)
    url += f"?next={next_url}"
    return url


class LogInTester:
    """Class support login in tests."""
 
    def _is_logged_in(self):
        """Returns True if a user is logged in.  False otherwise."""

        return '_auth_user_id' in self.client.session.keys()
