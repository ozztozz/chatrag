from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings


@override_settings(SECURE_SSL_REDIRECT=False)
class OAuthStateTests(TestCase):
	def test_login_stores_state_in_session_and_redirects_with_it(self):
		response = self.client.get('/auth/oauth/login/')

		self.assertEqual(response.status_code, 302)
		query = parse_qs(urlparse(response['Location']).query)
		self.assertIn('state', query)
		self.assertEqual(query['state'][0], self.client.session['instagram_oauth_state'])

	def test_callback_rejects_missing_state(self):
		response = self.client.get('/auth/oauth/callback/?code=code')

		self.assertEqual(response.status_code, 400)

	def test_callback_rejects_wrong_state(self):
		session = self.client.session
		session['instagram_oauth_state'] = 'expected-state'
		session.save()

		response = self.client.get('/auth/oauth/callback/?code=code&state=wrong-state')

		self.assertEqual(response.status_code, 400)
