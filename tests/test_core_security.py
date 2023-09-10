import unittest
from unittest.mock import Mock
from django.core.exceptions import PermissionDenied
from src.intrepid.security import (
    user_is_initiative_manager,
    _is_initiative_manager,
)


class TestUserIsInitiativeManager(unittest.TestCase):
    def setUp(self):
        self.request = Mock()
        self.initiative = Mock()
        self.initiative.users.all.return_value = [self.request.user]
        self.initiative.pk = 1

    def test_is_initiative_manager_staff(self):
        self.request.user.is_staff = True
        self.assertTrue(_is_initiative_manager(self.request, self.initiative))

    def test_is_initiative_manager_superuser(self):
        self.request.user.is_superuser = True
        self.assertTrue(_is_initiative_manager(self.request, self.initiative))

    def test_is_initiative_manager_user(self):
        self.request.user.is_staff = False
        self.request.user.is_superuser = False
        self.assertTrue(_is_initiative_manager(self.request, self.initiative))

    def test_is_not_initiative_manager(self):
        self.request.user.is_staff = False
        self.request.user.is_superuser = False
        self.initiative.users.all.return_value = [object()]
        self.assertFalse(_is_initiative_manager(self.request, self.initiative))

    def test_user_is_initiative_manager_decorator(self):
        func = Mock()
        self.request.user.is_staff = True
        wrapped_func = user_is_initiative_manager(func)
        wrapped_func(self.request, initiative_id=1)
        func.assert_called_once_with(self.request, initiative_id=1)

    def test_user_is_not_initiative_manager_decorator(self):
        func = Mock()
        self.request.user.is_staff = False
        self.request.user.is_superuser = False
        self.initiative.users.all.return_value = [object()]
        wrapped_func = user_is_initiative_manager(func)
        with self.assertRaises(PermissionDenied):
            wrapped_func(self.request, initiative_id=1)
        func.assert_not_called()


if __name__ == "__main__":
    unittest.main()
