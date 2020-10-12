# Generated by Django 2.2.15 on 2020-09-21 11:38

from django.db import migrations

from resolwe.flow.utils import iterate_fields


def purge_data_dependencies(apps, schema_editor):
    Data = apps.get_model("flow", "Data")
    DataDependency = apps.get_model("flow", "DataDependency")

    for data in Data.objects.iterator():
        parent_pks = []
        for field_schema, fields in iterate_fields(
            data.input, data.process.input_schema
        ):
            name = field_schema["name"]
            value = fields[name]

            if field_schema.get("type", "").startswith("data:"):
                parent_pks.append(value)

            elif field_schema.get("type", "").startswith("list:data:"):
                parent_pks.extend(value)

        parent_pks = [
            pk if Data.objects.filter(pk=pk).exists() else None for pk in parent_pks
        ]

        for dependency in DataDependency.objects.filter(child=data.id, kind="io"):
            parent_pk = dependency.parent.pk if dependency.parent else None
            if parent_pk in parent_pks:
                parent_pks.remove(parent_pk)
            else:
                dependency.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("flow", "0045_unreferenced_storages"),
    ]

    operations = [
        migrations.RunPython(purge_data_dependencies),
    ]
