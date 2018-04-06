import unittest


from stackility import CloudStackUtility
from stackility.cloudstackutility import CloudStackUtility

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



class TestUpsert(unittest.TestCase):

    def test_upsert(self):

        print('test_upsert')



