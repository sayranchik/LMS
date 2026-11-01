from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/new/", views.CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_update"),
    path("courses/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),
    path("courses/<int:course_pk>/modules/new/", views.ModuleCreateView.as_view(), name="module_create"),
    path("modules/<int:pk>/edit/", views.ModuleUpdateView.as_view(), name="module_update"),
    path("modules/<int:pk>/delete/", views.ModuleDeleteView.as_view(), name="module_delete"),
    path("modules/<int:module_pk>/lessons/new/", views.LessonCreateView.as_view(), name="lesson_create"),
    path("lessons/<int:pk>/", views.LessonDetailView.as_view(), name="lesson_detail"),
    path("lessons/<int:pk>/edit/", views.LessonUpdateView.as_view(), name="lesson_update"),
    path("lessons/<int:pk>/delete/", views.LessonDeleteView.as_view(), name="lesson_delete"),
]
