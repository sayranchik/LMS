from django.contrib import admin

from .models import Assignment, Submission

admin.site.register(Assignment)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "score", "submitted_at")
    list_filter = ("assignment",)
