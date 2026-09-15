from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authInstagram', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='token_error',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]