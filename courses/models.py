from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Course(models.Model):
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Опис")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Викладач", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="courses_taught",
        limit_choices_to={"role": "teacher"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Курс"
        verbose_name_plural = "Курси"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("course_detail", args=[self.pk])


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField("Назва", max_length=200)
    order = models.PositiveIntegerField("Порядок", default=1)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Модуль"
        verbose_name_plural = "Модулі"

    def __str__(self):
        return f"{self.course}: {self.title}"

    def get_absolute_url(self):
        return self.course.get_absolute_url()


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField("Назва", max_length=200)
    content = models.TextField("Текст уроку", blank=True)
    image = models.ImageField("Зображення", upload_to="lessons/", blank=True)
    video_url = models.URLField("Посилання на відео", blank=True)
    order = models.PositiveIntegerField("Порядок", default=1)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("lesson_detail", args=[self.pk])

    @property
    def video_embed_url(self):
        """Перетворює посилання YouTube на embed-URL; інші посилання повертає як є."""
        url = self.video_url
        if "youtube.com/watch?v=" in url:
            return "https://www.youtube.com/embed/" + url.split("watch?v=")[1].split("&")[0]
        if "youtu.be/" in url:
            return "https://www.youtube.com/embed/" + url.split("youtu.be/")[1].split("?")[0]
        return url


class Announcement(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    body = models.TextField("Текст")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Оголошення"
        verbose_name_plural = "Оголошення"

    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Опис", blank=True)
    starts_at = models.DateTimeField("Початок")

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "Подія"
        verbose_name_plural = "Події"

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self):
        return self.starts_at >= timezone.now()
