from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from assignments.models import Assignment, Submission

from .models import Course, Enrollment, Lesson, LessonProgress, Module


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
        # Базовый студент записан на курс; незаписанный — outsider.
        Enrollment.objects.create(student=cls.student, course=cls.course)
        cls.outsider = User.objects.create_user("outsider", password="pass12345", role=User.Role.STUDENT)


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


class EnrollmentTests(BaseLMSTestCase):
    def test_student_can_enroll_once(self):
        self.client.login(username="outsider", password="pass12345")
        url = reverse("course_enroll", args=[self.course.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.post(url)
        self.assertEqual(Enrollment.objects.filter(student=self.outsider).count(), 1)

    def test_enroll_requires_post(self):
        self.client.login(username="outsider", password="pass12345")
        resp = self.client.get(reverse("course_enroll", args=[self.course.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertFalse(Enrollment.objects.filter(student=self.outsider).exists())

    def test_enroll_requires_login(self):
        resp = self.client.post(reverse("course_enroll", args=[self.course.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_teacher_and_admin_cannot_enroll(self):
        for username in ("teacher", "admin1"):
            self.client.login(username=username, password="pass12345")
            resp = self.client.post(reverse("course_enroll", args=[self.course.pk]))
            self.assertEqual(resp.status_code, 403)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_unenroll_removes_enrollment_but_keeps_progress(self):
        LessonProgress.objects.create(student=self.student, lesson=self.lesson)
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("course_unenroll", args=[self.course.pk]))
        self.assertFalse(Enrollment.objects.filter(student=self.student).exists())
        self.assertTrue(LessonProgress.objects.filter(student=self.student).exists())

    def test_unenrolled_student_cannot_open_lesson_or_assignment(self):
        self.client.login(username="outsider", password="pass12345")
        resp = self.client.get(reverse("lesson_detail", args=[self.lesson.pk]))
        self.assertRedirects(resp, reverse("course_detail", args=[self.course.pk]))
        resp = self.client.get(reverse("assignment_detail", args=[self.assignment.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_unenrolled_student_cannot_submit(self):
        self.client.login(username="outsider", password="pass12345")
        resp = self.client.post(reverse("assignment_detail", args=[self.assignment.pk]), {"text": "x"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Submission.objects.filter(student=self.outsider).exists())

    def test_unenrolled_student_still_sees_course_page(self):
        self.client.login(username="outsider", password="pass12345")
        resp = self.client.get(reverse("course_detail", args=[self.course.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["has_access"])

    def test_teacher_and_admin_open_lessons_without_enrollment(self):
        for username in ("teacher", "admin1"):
            self.client.login(username=username, password="pass12345")
            self.assertEqual(self.client.get(reverse("lesson_detail", args=[self.lesson.pk])).status_code, 200)

    def test_course_students_page_permissions(self):
        url = reverse("course_students", args=[self.course.pk])
        self.client.login(username="student", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.login(username="teacher", password="pass12345")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["rows"]), 1)


class ProgressTests(BaseLMSTestCase):
    def setUp(self):
        self.lesson2 = Lesson.objects.create(module=self.module, title="Типи", order=2)
        self.client.login(username="student", password="pass12345")

    def test_complete_toggles_progress(self):
        url = reverse("lesson_complete", args=[self.lesson.pk])
        self.client.post(url)
        self.assertTrue(LessonProgress.objects.filter(student=self.student, lesson=self.lesson).exists())
        self.client.post(url)
        self.assertFalse(LessonProgress.objects.filter(student=self.student, lesson=self.lesson).exists())

    def test_progress_percent(self):
        self.assertEqual(self.course.progress_for(self.student), {"done": 0, "total": 2, "percent": 0})
        self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        self.assertEqual(self.course.progress_for(self.student), {"done": 1, "total": 2, "percent": 50})
        self.client.post(reverse("lesson_complete", args=[self.lesson2.pk]))
        self.assertEqual(self.course.progress_for(self.student)["percent"], 100)

    def test_progress_for_empty_course_is_zero(self):
        empty = Course.objects.create(title="Порожній", description="-")
        self.assertEqual(empty.progress_for(self.student), {"done": 0, "total": 0, "percent": 0})

    def test_progress_is_per_student(self):
        Enrollment.objects.create(student=self.outsider, course=self.course)
        self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        self.assertEqual(self.course.progress_for(self.outsider)["done"], 0)

    def test_unenrolled_cannot_complete_lesson(self):
        self.client.login(username="outsider", password="pass12345")
        resp = self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(LessonProgress.objects.filter(student=self.outsider).exists())

    def test_teacher_cannot_complete_lesson(self):
        self.client.login(username="teacher", password="pass12345")
        resp = self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_complete_requires_post(self):
        resp = self.client.get(reverse("lesson_complete", args=[self.lesson.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_course_detail_shows_progress_and_completed_lessons(self):
        self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        resp = self.client.get(reverse("course_detail", args=[self.course.pk]))
        self.assertEqual(resp.context["progress"]["percent"], 50)
        self.assertEqual(resp.context["completed_ids"], {self.lesson.pk})

    def test_my_courses_lists_enrolled_courses_with_progress(self):
        self.client.post(reverse("lesson_complete", args=[self.lesson.pk]))
        resp = self.client.get(reverse("my_courses"))
        self.assertEqual(resp.status_code, 200)
        (course, progress), = resp.context["rows"]
        self.assertEqual(course, self.course)
        self.assertEqual(progress["done"], 1)

    def test_deleting_lesson_removes_its_progress(self):
        self.client.post(reverse("lesson_complete", args=[self.lesson2.pk]))
        self.lesson2.delete()
        self.assertEqual(LessonProgress.objects.count(), 0)
