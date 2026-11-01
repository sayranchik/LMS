from django.urls import path

from . import views

urlpatterns = [
    path("grades/", views.GradeListView.as_view(), name="grade_list"),
    path("lesson/<int:lesson_pk>/new/", views.AssignmentCreateView.as_view(), name="assignment_create"),
    path("<int:pk>/", views.AssignmentDetailView.as_view(), name="assignment_detail"),
    path("<int:pk>/edit/", views.AssignmentUpdateView.as_view(), name="assignment_update"),
    path("<int:pk>/delete/", views.AssignmentDeleteView.as_view(), name="assignment_delete"),
    path("submission/<int:pk>/grade/", views.SubmissionGradeView.as_view(), name="submission_grade"),
]
