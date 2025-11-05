from collections import defaultdict
import django.db.models.deletion
from django.db import migrations, models


def article_set_chapter_fk(apps, schema_editor):
    Article = apps.get_model("elearning", "Article")
    Chapter = apps.get_model("elearning", "Chapter")

    # Mapping: module_id -> [chapter_id, ...] (sortiert nach id, passe Sortierung bei Bedarf an)
    chapters_by_module = defaultdict(list)
    for chapter_id, module_id in Chapter.objects.values_list("id", "module_id").order_by("id"):
        chapters_by_module[module_id].append(chapter_id)

    for article in Article.objects.only("id", "module_id").iterator():
        available_chapters = chapters_by_module.get(article.module_id) or []
        if available_chapters:
            first_chapter_id = available_chapters[0]
            Article.objects.filter(pk=article.pk).update(chapter_id=first_chapter_id)
        else:
            # Kein Kapitel für dieses Modul vorhanden → Standardkapitel anlegen
            default_title = f"Standardkapitel (Migration Artikel von Modul zu Kapitel)"

            new_chapter = Chapter.objects.create(
                module_id=article.module_id,
                title=default_title,
            )

            # Mapping aktualisieren, damit weitere Artikel dasselbe Kapitel verwenden
            chapters_by_module[article.module_id].append(new_chapter.id)

            # Artikel dem neu erstellten Standardkapitel zuordnen
            Article.objects.filter(pk=article.pk).update(chapter_id=new_chapter.id)

def assert_no_null_chapter(apps, schema_editor):
    Article = apps.get_model("elearning", "Article")
    missing = Article.objects.filter(chapter__isnull=True).count()
    if missing:
        raise RuntimeError(
            f"Chapter-FK noch NULL: Article={missing}"
            "Bitte Daten prüfen oder Mapping-Regel anpassen."
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "elearning",
            "0014_alter_content_chapter",
        ),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="article",
            unique_together=set(),
        ),
        # FK-Fields definieren (Nullable für Migration)
        migrations.AddField(
            model_name="article",
            name="chapter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text="Chapter this article belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="articles",
                to="elearning.chapter",
                verbose_name="Chapter",
            ),
        ),
        # Daten migrieren; Chapter-FK befüllen
        migrations.RunPython(
            article_set_chapter_fk, migrations.RunPython.noop
        ),
        # Fail-fast falls noch NULLs existieren
        migrations.RunPython(assert_no_null_chapter, migrations.RunPython.noop),
        # FK-Fields non-nullable machen
        migrations.AlterField(
            model_name="article",
            name="chapter",
            field=models.ForeignKey(
                blank=False,
                null=False,
                help_text="Chapter this article belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="articles",
                to="elearning.chapter",
                verbose_name="Chapter",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="article",
            unique_together={("chapter", "title")},
        ),
        migrations.RemoveField(
            model_name="article",
            name="module",
        ),
    ]
