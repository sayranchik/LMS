from django.contrib import admin

from .models import Announcement, Course, Enrollment, Event, Lesson, LessonProgress, Module

admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Announcement)
admin.site.register(Event)
admin.site.register(Enrollment)
admin.site.register(LessonProgress)
