# Generated by Django 2.2.4 on 2019-08-09 22:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of analysis', max_length=30, unique=True)),
                ('description', models.CharField(help_text='Description', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Preform',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of Preform', max_length=30, unique=True)),
                ('thickness', models.FloatField(default=0.01, help_text='Thickness')),
                ('K11', models.FloatField(default=1e-10, help_text='Enter a number for K11')),
                ('K12', models.FloatField(default=0, help_text='Enter a number for K12')),
                ('K22', models.FloatField(default=2e-10, help_text='Enter a number for K22')),
                ('analysis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preform', to='analyses.Analysis')),
            ],
        ),
        migrations.CreateModel(
            name='Step',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True)),
                ('typ', models.IntegerField(choices=[(0, 'Filling the mold'), (1, 'Time limit')], default=0)),
                ('endtime', models.FloatField(default=0, help_text='Time to end analysis')),
                ('analysis', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='step', to='analyses.Analysis')),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True)),
                ('rotate', models.FloatField(default=0, help_text='Degree of rotation')),
                ('analysis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='section', to='analyses.Analysis')),
                ('preform', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='preform', to='analyses.Preform')),
            ],
        ),
        migrations.CreateModel(
            name='Resin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of Resin', max_length=30, unique=True)),
                ('viscosity', models.FloatField(default=0.02, help_text='Enter a number for viscosity')),
                ('analysis', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='resin', to='analyses.Analysis')),
            ],
        ),
        migrations.CreateModel(
            name='Mesh',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of mesh', max_length=30, unique=True)),
                ('address', models.FileField(upload_to='meshfiles/')),
                ('analysis', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mesh', to='analyses.Analysis')),
            ],
        ),
        migrations.CreateModel(
            name='BC',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True)),
                ('typ', models.IntegerField(choices=[(0, 'Pressure'), (1, 'Flow Rate')], default=0)),
                ('value', models.FloatField(default=0, help_text='Value on Boundary Condition')),
                ('analysis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bc', to='analyses.Analysis')),
            ],
        ),
    ]
