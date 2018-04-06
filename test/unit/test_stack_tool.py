import unittest


from stackility import stack_tool
from stackility.stack_tool import StackTool

import json
from unittest.mock import patch
import os
from mock import Mock, MagicMock, patch
import mock
import tempfile
import shutil
import logging as log
import sys
import io
import boto3
from moto import mock_ssm



class TestPrintStack(unittest.TestCase):

    def test_print_stack_info(self):

        print('test_print_stack_info')



