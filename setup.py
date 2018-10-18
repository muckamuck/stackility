from setuptools import setup
setup(
    name="Stackility",
    version='0.6.1',
    packages=['stackility'],
    description='Python CloudFormation utility',
    author='Chuck Muckamuck',
    author_email='Chuck.Muckamuck@gmail.com',
    install_requires=[
        "boto3>=1.4.3",
        "requests>=2.18",
        "Click>=6.7",
        "PyYAML>=3.12",
        "pymongo>=3.4.0",
        "tabulate>=0.8",
        "configparser",
        "jinja2",
        "cloudformation-validator>=0.6"
    ],
    entry_points="""
        [console_scripts]
        stackility=stackility.command:cli
    """
)
