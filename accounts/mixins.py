from django.contrib.auth.mixins import UserPassesTestMixin


class AdminRequiredMixin(UserPassesTestMixin):
    """Доступ лише для адміністраторів LMS (403 для залогінених без прав)."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_lms_admin


class StaffRequiredMixin(UserPassesTestMixin):
    """Доступ для викладачів та адміністраторів."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_manage_assignments
