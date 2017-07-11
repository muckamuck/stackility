import os
from setuptools import setup, find_packages
setup(
    name="Stackility",
    version="0.1.0",
    packages=['stackility'],
    description='Python CloudFormation',
    author='Chuck Muckamuck',
    author_email='Chuck.Muckamuck@gmail.com',
    install_requires=[
        "boto3>=1.4.3",
        "Click>=6.7",
        "PyYAML>=3.12"
    ],
    entry_points="""
        [console_scripts]
        stackility=stackility.command:cli
    """
)
