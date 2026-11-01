from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)

from accounts.mixins import AdminRequiredMixin

from .forms import CourseForm, LessonForm, ModuleForm
from .models import Announcement, Course, Event, Lesson, Module


class HomeView(TemplateView):
    template_name = "courses/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["courses_count"] = Course.objects.count()
        ctx["new_courses"] = Course.objects.all()[:6]
        ctx["announcements"] = Announcement.objects.all()[:5]
        ctx["events"] = Event.objects.filter(starts_at__gte=timezone.now())[:5]
        return ctx


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    paginate_by = 12


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"

    def get_queryset(self):
        return Course.objects.prefetch_related("modules__lessons")


class CourseCreateView(AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "form.html"
    extra_context = {"title": "Новий курс"}


class CourseUpdateView(AdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "form.html"
    extra_context = {"title": "Редагування курсу"}


class CourseDeleteView(AdminRequiredMixin, DeleteView):
    model = Course
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return reverse("course_list")


class _ModuleParentMixin:
    """Підтягує курс із URL для створення модуля."""

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=kwargs["course_pk"])
        return super().dispatch(request, *args, **kwargs)


class ModuleCreateView(AdminRequiredMixin, _ModuleParentMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = "form.html"
    extra_context = {"title": "Новий модуль"}

    def form_valid(self, form):
        form.instance.course = self.course
        return super().form_valid(form)


class ModuleUpdateView(AdminRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = "form.html"
    extra_context = {"title": "Редагування модуля"}


class ModuleDeleteView(AdminRequiredMixin, DeleteView):
    model = Module
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return self.object.course.get_absolute_url()


class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = "courses/lesson_detail.html"

    def get_queryset(self):
        return Lesson.objects.select_related("module__course").prefetch_related("assignments")


class LessonCreateView(AdminRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "form.html"
    extra_context = {"title": "Новий урок"}

    def dispatch(self, request, *args, **kwargs):
        self.module = get_object_or_404(Module, pk=kwargs["module_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.module = self.module
        return super().form_valid(form)


class LessonUpdateView(AdminRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "form.html"
    extra_context = {"title": "Редагування уроку"}


class LessonDeleteView(AdminRequiredMixin, DeleteView):
    model = Lesson
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return self.object.module.course.get_absolute_url()
