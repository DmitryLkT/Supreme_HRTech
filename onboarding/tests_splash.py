from django.test import TestCase
from django.urls import reverse


class SplashTests(TestCase):
    def test_login_page_has_video_splash_and_logo(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, 'id="splash"')
        self.assertContains(response, "<video")
        self.assertContains(response, "/static/onboarding/video/splash.")
        self.assertContains(response, "/static/onboarding/css/splash.")
        self.assertContains(response, "/static/onboarding/js/splash.")
        self.assertContains(response, "/static/onboarding/img/altra-logo.")
