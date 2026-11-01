from django.contrib import admin

from .models import Announcement, Course, Event, Lesson, Module

admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Announcement)
admin.site.register(Event)
