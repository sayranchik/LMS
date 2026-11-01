from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from courses.models import Lesson


class Assignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Умова")
    due_date = models.DateTimeField("Термін здачі", null=True, blank=True)
    max_score = models.PositiveIntegerField("Максимальний бал", default=100)

    class Meta:
        ordering = ["id"]
        verbose_name = "Завдання"
        verbose_name_plural = "Завдання"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("assignment_detail", args=[self.pk])


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    text = models.TextField("Відповідь", blank=True)
    file = models.FileField("Файл", upload_to="submissions/", blank=True)
    submitted_at = models.DateTimeField(auto_now=True)
    score = models.PositiveIntegerField("Оцінка", null=True, blank=True)
    feedback = models.TextField("Коментар викладача", blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="graded_submissions",
    )

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "student"], name="one_submission_per_student"),
        ]
        verbose_name = "Робота студента"
        verbose_name_plural = "Роботи студентів"

    def __str__(self):
        return f"{self.student} — {self.assignment}"

    def clean(self):
        if self.score is not None and self.assignment_id and self.score > self.assignment.max_score:
            raise ValidationError(
                {"score": f"Оцінка не може перевищувати {self.assignment.max_score}."}
            )

    @property
    def is_graded(self):
        return self.score is not None
