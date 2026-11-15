from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)

from accounts.mixins import AdminRequiredMixin, StaffRequiredMixin

from .forms import CourseForm, LessonForm, ModuleForm
from .models import (Announcement, Course, Enrollment, Event, Lesson,
                     LessonProgress, Module)


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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["enrolled_ids"] = (
            set(user.enrollments.values_list("course_id", flat=True)) if user.is_student else set()
        )
        return ctx


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"

    def get_queryset(self):
        return Course.objects.prefetch_related("modules__lessons")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        course = self.object
        ctx["has_access"] = user.has_course_access(course)
        ctx["is_student"] = user.is_student
        if user.is_student:
            ctx["is_enrolled"] = ctx["has_access"]
            ctx["completed_ids"] = set(
                LessonProgress.objects.filter(student=user, lesson__module__course=course)
                .values_list("lesson_id", flat=True)
            )
            ctx["progress"] = course.progress_for(user)
        return ctx


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

    def get(self, request, *args, **kwargs):
        lesson = self.get_object()
        course = lesson.module.course
        if not request.user.has_course_access(course):
            messages.info(request, "Запишіться на курс, щоб відкрити його уроки.")
            return redirect(course)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["is_student"] = user.is_student
        if user.is_student:
            ctx["is_completed"] = LessonProgress.objects.filter(
                student=user, lesson=self.object
            ).exists()
        return ctx


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


# --- Запис на курс і прогрес ---------------------------------------------------

def _require_student(user):
    if not user.is_student:
        raise PermissionDenied("Ця дія доступна лише студентам.")


@login_required
@require_POST
def course_enroll(request, pk):
    _require_student(request.user)
    course = get_object_or_404(Course, pk=pk)
    _, created = Enrollment.objects.get_or_create(student=request.user, course=course)
    if created:
        messages.success(request, f"Ви записані на курс «{course.title}».")
    return redirect(course)


@login_required
@require_POST
def course_unenroll(request, pk):
    _require_student(request.user)
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.filter(student=request.user, course=course).delete()
    messages.info(request, f"Запис на курс «{course.title}» скасовано. Ваш прогрес збережено.")
    return redirect(course)


@login_required
@require_POST
def lesson_complete(request, pk):
    """Перемикає позначку «урок пройдено»."""
    _require_student(request.user)
    lesson = get_object_or_404(Lesson.objects.select_related("module__course"), pk=pk)
    if not request.user.has_course_access(lesson.module.course):
        raise PermissionDenied("Спочатку запишіться на курс.")
    progress, created = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
    if not created:
        progress.delete()
    return redirect(lesson)


class MyCoursesView(LoginRequiredMixin, TemplateView):
    template_name = "courses/my_courses.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        rows = []
        if user.is_student:
            enrollments = user.enrollments.select_related("course")
            rows = [(e.course, e.course.progress_for(user)) for e in enrollments]
        ctx["rows"] = rows
        return ctx


class CourseStudentsView(StaffRequiredMixin, DetailView):
    """Викладач/адмін бачать записаних студентів та їхній прогрес."""

    model = Course
    template_name = "courses/course_students.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rows"] = [
            (e, self.object.progress_for(e.student))
            for e in self.object.enrollments.select_related("student")
        ]
        return ctx
