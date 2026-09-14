from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from main.models import MessageJob
from main.conversation_graph import generate_conversation_response
from main.views import (
    get_instagram_user_info,
    send_and_save_reply,
    send_writing_indicator,
)


class Command(BaseCommand):
    help = 'Process pending Instagram message jobs.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=5)

    def handle(self, *args, **options):
        limit = max(1, min(options['limit'], 50))
        stale_before = timezone.now() - timedelta(minutes=10)
        MessageJob.objects.filter(
            status=MessageJob.STATUS_PROCESSING,
            locked_at__lt=stale_before,
        ).update(status=MessageJob.STATUS_PENDING, locked_at=None)

        processed = 0
        for _ in range(limit):
            with transaction.atomic():
                job = (MessageJob.objects.select_for_update().select_related('message__user')
                       .filter(status=MessageJob.STATUS_PENDING)
                       .order_by('updated_at')
                       .first())
                if not job:
                    break
                job.status = MessageJob.STATUS_PROCESSING
                job.attempts += 1
                job.locked_at = timezone.now()
                job.save(update_fields=['status', 'attempts', 'locked_at', 'updated_at'])

            self.process_job(job)
            processed += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {processed} message job(s).'))

    def process_job(self, job):
        message = job.message
        user = message.user
        try:
            try:
                user_info = get_instagram_user_info(user.instagram_id)
                user.name = user_info.get('name')
                user.username = user_info.get('username')
                user.is_user_follow_business = user_info.get('is_user_follow_business', False)
                user.save(update_fields=['name', 'username', 'is_user_follow_business'])
            except Exception:
                if user.is_user_follow_business:
                    raise

            if user.is_user_follow_business:
                job.status = MessageJob.STATUS_COMPLETED
                job.locked_at = None
                job.save(update_fields=['status', 'locked_at', 'updated_at'])
                return

            send_writing_indicator(user.instagram_id)
            reply_text = generate_conversation_response(user, message.text)
            if not reply_text:
                raise RuntimeError('All Gemini models failed to generate a response')
            if not send_and_save_reply(user, reply_text):
                raise RuntimeError('Instagram reply was rejected')

            job.status = MessageJob.STATUS_COMPLETED
            job.locked_at = None
            job.last_error = ''
            job.save(update_fields=['status', 'locked_at', 'last_error', 'updated_at'])
        except Exception as exc:
            job.status = (
                MessageJob.STATUS_FAILED
                if job.attempts >= 3
                else MessageJob.STATUS_PENDING
            )
            job.locked_at = None
            job.last_error = str(exc)[:2000]
            job.save(update_fields=['status', 'locked_at', 'last_error', 'updated_at'])
            self.stderr.write(f'Job {job.pk} failed: {exc}')
