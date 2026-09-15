from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authInstagram', '0001_initial'),
        ('main', '0003_messagejob'),
    ]

    operations = [
        migrations.AddField(
            model_name='instagrammessage',
            name='account',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='authInstagram.useraccount',
            ),
        ),
    ]