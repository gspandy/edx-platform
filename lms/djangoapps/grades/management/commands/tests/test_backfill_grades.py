"""
Tests for reset_grades management command.
"""

# pylint: disable=protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import ddt
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase
from mock import patch, MagicMock
import six

from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from student.models import CourseEnrollment
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from lms.djangoapps.grades.management.commands import backfill_grades


@ddt.ddt
class TestComputeGrades(SharedModuleStoreTestCase):
    """
    Tests generate course blocks management command.
    """
    num_users = 3
    num_courses = 5

    @classmethod
    def setUpClass(cls):
        super(TestComputeGrades, cls).setUpClass()
        User = get_user_model()  # pylint: disable=invalid-name
        cls.command = backfill_grades.Command()

        cls.courses = [CourseFactory.create(run='test_{}'.format(idx)) for idx in range(cls.num_courses)]
        cls.users = [User.objects.create(username='user{}'.format(idx)) for idx in range(cls.num_users)]

        for user in cls.users:
            for course in cls.courses:
                CourseEnrollment.enroll(user, course.id)

    def test_all_course_selection(self):
        courses = self.command._get_course_keys({'all_courses': True})
        self.assertEqual(
            sorted(six.text_type(course) for course in courses),
            [
                'org.0/course_0/test_0',
                'org.1/course_1/test_1',
                'org.2/course_2/test_2',
                'org.3/course_3/test_3',
                'org.4/course_4/test_4',
            ]
        )

    def test_explicit_course_selection(self):
        courses = self.command._get_course_keys(
            {'courses': ['org.0/course_0/test_0', 'org.1/course_1/test_1']}
        )
        self.assertEqual(
            sorted(six.text_type(course) for course in courses),
            [
                'org.0/course_0/test_0',
                'org.1/course_1/test_1',
            ]
        )

    @ddt.data(
        'badcoursekey',
        'non/existent/course',
    )
    def test_selecting_invalid_course(self, badcourse):
        with self.assertRaises(CommandError):
            self.command._get_course_keys({'courses': ['org.0/course_0/test_0', 'org.1/course_1/test_1', badcourse]})

    @patch('lms.djangoapps.grades.tasks.backfill_grades_for_course')
    def test_tasks_fired(self, mock_task):
        print(dir(mock_task))
        call_command('backfill_grades', '--batch_size=2', '--course', 'org.0/course_0/test_0', 'org.3/course_3/test_3')
        # 2 courses x 2 batches per course = 4
        self.assertEqual(mock_task.apply_async.call_count, 4)
        self.assertEqual(
            mock_task.apply_async.call_args_list,
            [
                ({'options': {}, 'kwargs': {'course_key': 'org.0/course_0/test_0', 'batch_size': 2, 'offset': 0}},),
                ({'options': {}, 'kwargs': {'course_key': 'org.0/course_0/test_0', 'batch_size': 2, 'offset': 2}},),
                ({'options': {}, 'kwargs': {'course_key': 'org.3/course_3/test_3', 'batch_size': 2, 'offset': 0}},),
                ({'options': {}, 'kwargs': {'course_key': 'org.3/course_3/test_3', 'batch_size': 2, 'offset': 2}},),
            ],
        )
