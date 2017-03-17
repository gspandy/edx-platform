"""
Asynchronous tasks related to the Course Blocks sub-application.
"""
import logging

from capa.responsetypes import LoncapaProblemError
from celery.task import task
from django.conf import settings
from lxml.etree import XMLSyntaxError

from edxval.api import ValInternalError
from opaque_keys.edx.keys import CourseKey

from xmodule.modulestore.exceptions import ItemNotFoundError
from openedx.core.djangoapps.content.block_structure import api
from openedx.core.djangoapps.content.block_structure.config import STORAGE_BACKING_FOR_CACHE, enable_for_current_request

log = logging.getLogger('edx.celery.task')

# TODO: TNL-5799 is ongoing; narrow these lists down until the general exception is no longer needed
RETRY_TASKS = (ItemNotFoundError, TypeError, ValInternalError)
NO_RETRY_TASKS = (XMLSyntaxError, LoncapaProblemError, UnicodeEncodeError)


def block_structure_task():
    """
    Decorator for block structure tasks.
    """
    return task(
        default_retry_delay=settings.BLOCK_STRUCTURES_SETTINGS['TASK_DEFAULT_RETRY_DELAY'],
        max_retries=settings.BLOCK_STRUCTURES_SETTINGS['TASK_MAX_RETRIES'],
        bind=True,
    )


@block_structure_task()
def update_course_in_cache_v2(self, **kwargs):
    """
    Updates the course blocks (in the database) for the specified course.
    """
    _update_course_in_cache(self, **kwargs)


@block_structure_task()
def update_course_in_cache(self, course_id):
    """
    Updates the course blocks (in the database) for the specified course.
    """
    _update_course_in_cache(self, course_id=course_id)


def _update_course_in_cache(self, **kwargs):
    """
    Updates the course blocks (in the database) for the specified course.
    """
    if kwargs.get('with_storage'):
        enable_for_current_request(STORAGE_BACKING_FOR_CACHE)
    _call_and_retry_if_needed(kwargs['course_id'], api.update_course_in_cache, update_course_in_cache, self.request.id)


@block_structure_task()
def get_course_in_cache_v2(self, **kwargs):
    """
    Gets the course blocks for the specified course, updating the cache if needed.
    """
    _get_course_in_cache(self, **kwargs)


@block_structure_task()
def get_course_in_cache(self, course_id):
    """
    Gets the course blocks for the specified course, updating the cache if needed.
    """
    _get_course_in_cache(self, course_id=course_id)


def _get_course_in_cache(self, **kwargs):
    """
    Gets the course blocks for the specified course, updating the cache if needed.
    """
    if kwargs.get('with_storage'):
        enable_for_current_request(STORAGE_BACKING_FOR_CACHE)
    _call_and_retry_if_needed(kwargs['course_id'], api.get_course_in_cache, get_course_in_cache, self.request.id)


def _call_and_retry_if_needed(course_id, api_method, task_method, task_id):
    """
    Calls the given api_method with the given course_id, retrying task_method upon failure.
    """
    try:
        course_key = CourseKey.from_string(course_id)
        api_method(course_key)
    except NO_RETRY_TASKS:
        # Known unrecoverable errors
        log.exception(
            "%s encountered unrecoverable error in course {}, task_id {}".format(
                task_method.__name__,
                course_id,
                task_id
            )
        )
        raise
    except RETRY_TASKS as exc:
        log.exception("%s encountered expected error, retrying.", task_method.__name__)
        raise task_method.retry(args=[course_id], exc=exc)
    except Exception as exc:   # pylint: disable=broad-except
        log.exception(
            "%s encountered unknown error. Retry #%d",
            task_method.__name__,
            task_method.request.retries,
        )
        raise task_method.retry(args=[course_id], exc=exc)
