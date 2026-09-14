import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import InstagramMessage, InstagramUser, MessageJob
from .views import get_gemini_messages
from .conversation_graph import conversation_graph


@override_settings(INSTAGRAM_APP_SECRET='test-app-secret', SECURE_SSL_REDIRECT=False)
class InstagramWebhookSignatureTests(TestCase):
	def test_webhook_rejects_missing_signature(self):
		response = self.client.post(
			'/instagram/webhook/',
			data='{"object": "other"}',
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 403)

	def test_webhook_rejects_invalid_signature(self):
		response = self.client.post(
			'/instagram/webhook/',
			data='{"object": "other"}',
			content_type='application/json',
			HTTP_X_HUB_SIGNATURE_256='sha256=invalid',
		)

		self.assertEqual(response.status_code, 403)

	def test_webhook_accepts_valid_signature(self):
		body = b'{"object": "other"}'
		signature = hmac.new(b'test-app-secret', body, hashlib.sha256).hexdigest()

		response = self.client.post(
			'/instagram/webhook/',
			data=body,
			content_type='application/json',
			HTTP_X_HUB_SIGNATURE_256=f'sha256={signature}',
		)

		self.assertEqual(response.status_code, 200)

	def test_webhook_queues_incoming_message(self):
		body = b'{"object":"instagram","entry":[{"messaging":[{"sender":{"id":"sender-1"},"recipient":{"id":"business-1"},"message":{"mid":"mid-1","text":"Merhaba"}}]}]}'
		signature = hmac.new(b'test-app-secret', body, hashlib.sha256).hexdigest()

		response = self.client.post(
			'/instagram/webhook/',
			data=body,
			content_type='application/json',
			HTTP_X_HUB_SIGNATURE_256=f'sha256={signature}',
		)

		self.assertEqual(response.status_code, 200)
		message = InstagramMessage.objects.get(message_id='mid-1')
		self.assertTrue(MessageJob.objects.filter(message=message, status=MessageJob.STATUS_PENDING).exists())


@override_settings(GEMINI_MODELS=['first-model', 'fallback-model'])
class GeminiFallbackTests(TestCase):
	@patch('main.views.time.sleep')
	@patch('main.views.genai.Client')
	@patch('main.views.get_old_messages', return_value=[])
	def test_fallback_model_is_used_after_primary_retries(self, mocked_history, mocked_client, mocked_sleep):
		primary_chat = _FakeChat([SimpleNamespace(text=''), SimpleNamespace(text=''), SimpleNamespace(text='')])
		fallback_chat = _FakeChat([SimpleNamespace(text='Fallback cevap')])
		mocked_client.return_value.chats.create.side_effect = [primary_chat, fallback_chat]
		user = InstagramUser.objects.create(instagram_id='gemini-user')

		result = get_gemini_messages(user, 'Merhaba')

		self.assertEqual(result, 'Fallback cevap')
		self.assertEqual(primary_chat.calls, 3)
		self.assertEqual(fallback_chat.calls, 1)


class _FakeChat:
	def __init__(self, responses):
		self.responses = responses
		self.calls = 0

	def send_message(self, message):
		response = self.responses[self.calls]
		self.calls += 1
		return response


@override_settings(SECURE_SSL_REDIRECT=False)
class ConversationGraphTests(TestCase):
	@patch('main.views.get_gemini_messages', return_value='Yanıt')
	def test_graph_routes_appointment_message(self, mocked_generator):
		user = InstagramUser.objects.create(instagram_id='graph-user')

		result = conversation_graph.invoke({
			'user_obj': user,
			'new_message': 'Randevu almak istiyorum',
		})

		self.assertEqual(result['stage'], 'appointment')
		self.assertEqual(result['response'], 'Yanıt')
		self.assertIn('Randevu akışını uygula', mocked_generator.call_args.kwargs['additional_instruction'])

	@patch('main.views.get_gemini_messages', return_value='Yanıt')
	def test_graph_routes_rejection_to_closing(self, mocked_generator):
		user = InstagramUser.objects.create(instagram_id='closing-user')

		result = conversation_graph.invoke({
			'user_obj': user,
			'new_message': 'Hayır, teşekkürler',
		})

		self.assertEqual(result['stage'], 'closing')
		self.assertIn('0506 480 20 24', mocked_generator.call_args.kwargs['additional_instruction'])
