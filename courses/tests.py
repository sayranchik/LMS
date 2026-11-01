from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from assignments.models import Assignment, Submission

from .models import Course, Lesson, Module


class BaseLMSTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user("student", password="pass12345", role=User.Role.STUDENT)
        cls.teacher = User.objects.create_user("teacher", password="pass12345", role=User.Role.TEACHER)
        cls.admin = User.objects.create_user("admin1", password="pass12345", role=User.Role.ADMIN)
        cls.course = Course.objects.create(title="Python", description="Основи", teacher=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title="Вступ", order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title="Змінні", content="text", order=1)
        cls.assignment = Assignment.objects.create(
            lesson=cls.lesson, title="ДЗ 1", description="Зробіть", max_score=10
        )


class AccessTests(BaseLMSTestCase):
    def test_home_is_public(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_course_list_requires_login(self):
        resp = self.client.get(reverse("course_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_student_can_view_courses_and_lessons(self):
        self.client.login(username="student", password="pass12345")
        self.assertEqual(self.client.get(reverse("course_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("course_detail", args=[self.course.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("lesson_detail", args=[self.lesson.pk])).status_code, 200)

    def test_student_and_teacher_cannot_edit_courses(self):
        for username in ("student", "teacher"):
            self.client.login(username=username, password="pass12345")
            self.assertEqual(self.client.get(reverse("course_create")).status_code, 403)
            self.assertEqual(self.client.post(reverse("course_delete", args=[self.course.pk])).status_code, 403)
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_admin_can_create_edit_delete_course(self):
        self.client.login(username="admin1", password="pass12345")
        resp = self.client.post(reverse("course_create"), {"title": "Django", "description": "Web"})
        self.assertEqual(resp.status_code, 302)
        course = Course.objects.get(title="Django")
        self.client.post(reverse("course_update", args=[course.pk]), {"title": "Django 2", "description": "Web"})
        course.refresh_from_db()
        self.assertEqual(course.title, "Django 2")
        self.client.post(reverse("course_delete", args=[course.pk]))
        self.assertFalse(Course.objects.filter(pk=course.pk).exists())

    def test_admin_can_manage_modules_and_lessons(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(reverse("module_create", args=[self.course.pk]), {"title": "Мод 2", "order": 2})
        module = Module.objects.get(title="Мод 2")
        self.client.post(reverse("lesson_create", args=[module.pk]), {"title": "Урок X", "order": 1})
        self.assertTrue(Lesson.objects.filter(title="Урок X", module=module).exists())
        self.client.post(reverse("module_delete", args=[module.pk]))
        self.assertFalse(Lesson.objects.filter(title="Урок X").exists())


class AuthTests(BaseLMSTestCase):
    def test_registration_creates_student_even_if_role_posted(self):
        resp = self.client.post(reverse("register"), {
            "username": "newbie", "first_name": "Н", "last_name": "К", "email": "n@example.com",
            "password1": "StrongPass#2026", "password2": "StrongPass#2026", "role": "admin",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newbie")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.is_lms_admin)

    def test_profile_update_changes_only_own_data(self):
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("profile"), {"first_name": "Іван", "last_name": "Іванов", "email": "i@example.com", "bio": "hi"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Іван")
        self.assertEqual(self.student.role, User.Role.STUDENT)

    def test_profile_cannot_escalate_role(self):
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("profile"), {"first_name": "A", "last_name": "B", "email": "a@example.com", "role": "admin"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Role.STUDENT)


class AssignmentTests(BaseLMSTestCase):
    def test_student_submits_and_updates_single_submission(self):
        self.client.login(username="student", password="pass12345")
        url = reverse("assignment_detail", args=[self.assignment.pk])
        self.client.post(url, {"text": "відповідь 1"})
        self.client.post(url, {"text": "відповідь 2"})
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 1)
        self.assertEqual(Submission.objects.get(student=self.student).text, "відповідь 2")

    def test_empty_submission_rejected(self):
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("assignment_detail", args=[self.assignment.pk]), {"text": ""})
        self.assertFalse(Submission.objects.exists())

    def test_teacher_grades_and_student_cannot(self):
        sub = Submission.objects.create(assignment=self.assignment, student=self.student, text="x")
        url = reverse("submission_grade", args=[sub.pk])
        self.client.login(username="student", password="pass12345")
        self.assertEqual(self.client.post(url, {"score": 10}).status_code, 403)
        self.client.login(username="teacher", password="pass12345")
        self.assertEqual(self.client.post(url, {"score": 8, "feedback": "ok"}).status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.score, 8)
        self.assertEqual(sub.graded_by, self.teacher)

    def test_score_above_max_rejected(self):
        sub = Submission.objects.create(assignment=self.assignment, student=self.student, text="x")
        self.client.login(username="teacher", password="pass12345")
        self.client.post(reverse("submission_grade", args=[sub.pk]), {"score": 11})
        sub.refresh_from_db()
        self.assertIsNone(sub.score)

    def test_admin_can_edit_grade(self):
        sub = Submission.objects.create(assignment=self.assignment, student=self.student, text="x", score=5)
        self.client.login(username="admin1", password="pass12345")
        self.client.post(reverse("submission_grade", args=[sub.pk]), {"score": 9})
        sub.refresh_from_db()
        self.assertEqual(sub.score, 9)

    def test_graded_submission_is_locked_for_student(self):
        sub = Submission.objects.create(assignment=self.assignment, student=self.student, text="old", score=7)
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("assignment_detail", args=[self.assignment.pk]), {"text": "new"})
        sub.refresh_from_db()
        self.assertEqual(sub.text, "old")

    def test_student_sees_only_own_grades(self):
        other = User.objects.create_user("other", password="pass12345")
        Submission.objects.create(assignment=self.assignment, student=other, text="o", score=1)
        mine = Submission.objects.create(assignment=self.assignment, student=self.student, text="m", score=2)
        self.client.login(username="student", password="pass12345")
        resp = self.client.get(reverse("grade_list"))
        self.assertEqual(list(resp.context["submissions"]), [mine])
