#!/usr/bin/env python
"""
This module will execute the py.test test suite.
Run this script with --help to see all command line options.
"""
import argparse
import os
import subprocess
import re


project_dir = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.join(project_dir, 'test')

package_name = 'stackility'

package_dir = os.path.join(project_dir, package_name)


os.environ["PYTHONPATH"] = project_dir


def run_tests(report=False, pylint=True, tests=True, test_path=test_dir):
    """
    Run the tests and output a report if the user wants one.
    """
    if report:
        subprocess.check_call(['py.test',
                         '--junit-xml=test-reports/py.test-latest.xml',
                         '--cov', package_dir,
                         '--cov-report', 'xml',
                         test_path])
    elif tests:
        subprocess.check_call(['py.test', test_path])

    if pylint:
        pylint_target = os.path.realpath(test_path)
        if pylint_target == test_dir:
            pylint_target = package_dir
        elif pylint_target.startswith(test_dir):
            return

        pylintrc_path = os.path.join(project_dir, '.local_pylintrc')
        subprocess.check_call(['py.test', '--pylint', '--pylint-rcfile', pylintrc_path, '-m', 'pylint', pylint_target])


def main():
    """
    Function to run if invoked from the command line.
    """
    parser = argparse.ArgumentParser(description="Runs integration test suite")
    parser.add_argument(
        '-r', '--reports',
        dest='report',
        help="Print a junit report.",
        action='store_true'
    )
    parser.add_argument(
        '-n', '--no-pylint',
        dest='pylint',
        help='Skip the pylint checks.',
        action='store_false'
    )
    parser.add_argument(
        '-s', '--skip-tests',
        dest='tests',
        help='Skip the unit tests',
        action='store_false'
    )
    parser.add_argument(
        '-p', '--test-path',
        dest='test_path',
        default='./test',
        help="Run a specific test or test directory rather than the whole suite"
    )
    arguments = parser.parse_args()

    run_tests(arguments.report, arguments.pylint, arguments.tests, arguments.test_path)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode)

