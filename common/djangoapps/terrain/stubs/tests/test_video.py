"""
Unit tests for Video stub server implementation.
"""
import unittest
import requests
from ..video_source import VideoSourceHttpService

@ddt.ddt
class StubVideoServiceTest(unittest.TestCase):
    """
    Test cases for the video stub service.
    """
    def setUp(self):
        """
        Start the stub server.
        """
        super(StubVideoServiceTest, self).setUp()
        self.server = VideoSourceHttpService()
        self.addCleanup(self.server.shutdown)

    def test_correct_header_is_present(self):
        """
        Verify that `Access-Control-Allow-Origin` header is set.
        """
        pass
        # from nose.tools import set_trace; set_trace()
        # response = requests.head("http://127.0.0.1:{port}/hls/history.m3u8".format(port=self.server.port))

    def test_get_hls_manifest(self):
        """
        Verify that hls manifest is received.
        """
        pass