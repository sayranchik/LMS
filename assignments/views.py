from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin
from courses.models import Lesson

from .forms import AssignmentForm, GradeForm, SubmissionForm
from .models import Assignment, Submission


class AssignmentCreateView(StaffRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = "form.html"
    extra_context = {"title": "Нове завдання"}

    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(Lesson, pk=kwargs["lesson_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.lesson = self.lesson
        return super().form_valid(form)


class AssignmentUpdateView(StaffRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = "form.html"
    extra_context = {"title": "Редагування завдання"}


class AssignmentDeleteView(StaffRequiredMixin, DeleteView):
    model = Assignment
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return self.object.lesson.get_absolute_url()


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    """Студент бачить умову й форму здачі, викладач/адмін — список робіт."""

    model = Assignment
    template_name = "assignments/assignment_detail.html"

    def get_object(self, queryset=None):
        assignment = super().get_object(queryset)
        course = assignment.lesson.module.course
        if not self.request.user.has_course_access(course):
            raise PermissionDenied("Спочатку запишіться на курс.")
        return assignment

    def _own_submission(self):
        return Submission.objects.filter(
            assignment=self.object, student=self.request.user
        ).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.can_manage_assignments:
            ctx["submissions"] = self.object.submissions.select_related("student")
        else:
            submission = self._own_submission()
            ctx["submission"] = submission
            if submission is None or not submission.is_graded:
                ctx["form"] = kwargs.get("form") or SubmissionForm(instance=submission)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.can_manage_assignments:
            return HttpResponseForbidden("Лише студенти здають завдання.")
        submission = self._own_submission()
        if submission and submission.is_graded:
            messages.error(request, "Оцінену роботу змінювати не можна.")
            return redirect(self.object)
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.assignment = self.object
            sub.student = request.user
            sub.save()
            messages.success(request, "Роботу збережено.")
            return redirect(self.object)
        ctx = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(ctx)


class SubmissionGradeView(StaffRequiredMixin, UpdateView):
    """Викладачі виставляють оцінки, адміністратори можуть їх переглядати й редагувати."""

    model = Submission
    form_class = GradeForm
    template_name = "assignments/grade_form.html"

    def form_valid(self, form):
        form.instance.graded_by = self.request.user
        messages.success(self.request, "Оцінку збережено.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.assignment.get_absolute_url()


class GradeListView(LoginRequiredMixin, ListView):
    """Студент бачить свої оцінки, викладач/адмін — усі роботи."""

    template_name = "assignments/grade_list.html"
    context_object_name = "submissions"
    paginate_by = 30

    def get_queryset(self):
        qs = Submission.objects.select_related("assignment__lesson__module__course", "student")
        user = self.request.user
        if user.can_manage_assignments:
            return qs
        return qs.filter(student=user)
