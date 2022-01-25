"""
The command line interface to stackility.

Major help from: https://www.youtube.com/watch?v=kNke39OZ2k0
"""
# pylint: disable=broad-except
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=logging-format-interpolation


from configparser import RawConfigParser
import time
import json
import logging
import sys
import os
import traceback
import boto3
import click
from stackility import CloudStackUtility
from stackility import StackTool
from stackility import DriftTool
from stackility import ResourceTool

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
    datefmt='%Y/%m/%d-%H:%M:%S'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@click.group()
@click.version_option(version='0.8.1')
def cli():
    """
    A utility for creating, updating, listing and deleting AWS CloudFormation stacks.
    """
    logger.debug('cli() called')


@cli.command()
@click.option('--version', '-v', help='code version')
@click.option('--stack', '-s', help='stack name')
@click.option('--ini', '-i', help='INI file with needed information', required=True)
@click.option('--dryrun', '-d', help='dry run, generate a change set report', is_flag=True)
@click.option(
    '--yaml', '-y',
    help='YAML template (deprecated - YAMLness is now detected at run-time)',
    is_flag=True
)
@click.option('--no-poll', help='Start the stack work but do not poll', is_flag=True)
@click.option('--work-directory', '-w', help='Start in the given working directory')
def upsert(version, stack, ini, dryrun, yaml, no_poll, work_directory):
    """
    The main reason we have arrived here. This is the entry-point for the
    utility to create/update a CloudFormation stack.
    """
    ini_data = read_config_info(ini)
    if 'environment' not in ini_data:
        print('[environment] section is required in the INI file')
        sys.exit(1)

    if version:
        ini_data['codeVersion'] = version
    else:
        ini_data['codeVersion'] = str(int(time.time()))

    if 'region' not in ini_data['environment']:
        ini_data['environment']['region'] = find_myself()

    ini_data['yaml'] = bool(yaml)
    ini_data['no_poll'] = bool(no_poll)
    ini_data['dryrun'] = bool(dryrun)

    if stack:
        ini_data['environment']['stack_name'] = stack

    if work_directory:
        try:
            os.chdir(work_directory)
        except Exception as wtf:
            logger.error(wtf)
            sys.exit(2)

    print(json.dumps(ini_data, indent=2))
    start_upsert(ini_data)


@cli.command()
@click.option('-s', '--stack', required=True)
@click.option('-r', '--region')
@click.option('-f', '--profile')
def delete(stack, region, profile):
    """
    Delete the given CloudFormation stack.
    """
    ini_data = {}
    environment = {}

    environment['stack_name'] = stack
    if region:
        environment['region'] = region
    else:
        environment['region'] = find_myself()

    if profile:
        environment['profile'] = profile

    ini_data['environment'] = environment

    if start_smash(ini_data):
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.option('-r', '--region')
@click.option('-f', '--profile')
def list(region, profile):
    """
    List all the CloudFormation stacks in the given region.
    """
    ini_data = {}
    environment = {}

    if region:
        environment['region'] = region
    else:
        environment['region'] = find_myself()

    if profile:
        environment['profile'] = profile

    ini_data['environment'] = environment
    if start_list(ini_data):
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.option('--stack', '-s', help='stack name', required=True)
@click.option('-r', '--region', help='region where the stack lives')
@click.option('-f', '--profile', help='AWS profile to access resources')
def drift(stack, region, profile):
    """
    Produce a CloudFormation drift report for the given stack.
    """
    logger.debug('finding drift - stack: {}'.format(stack))
    logger.debug('region: {}'.format(region))
    logger.debug('profile: {}'.format(profile))
    tool = DriftTool(
        Stack=stack,
        Region=region,
        Profile=profile,
        Verbose=True
    )

    if tool.determine_drift():
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.option('--stack', '-s', help='stack name', required=True)
@click.option('-r', '--region', help='region where the stack lives')
@click.option('-f', '--profile', help='AWS profile to access resources')
def resources(stack, region, profile):
    """
    Produce a CloudFormation drift report for the given stack.
    """
    logging.debug('finding resources - stack: {}'.format(stack))
    logging.debug('region: {}'.format(region))
    logging.debug('profile: {}'.format(profile))
    tool = ResourceTool(
        Stack=stack,
        Region=region,
        Profile=profile,
        Verbose=True
    )

    if tool.list_resources():
        sys.exit(0)
    else:
        sys.exit(1)


def start_upsert(ini_data):
    """
    Helper function to facilitate upsert.

    Args:
        ini_date - the dictionary of info to run upsert

   Exit:
       0 - good
       1 - bad
    """
    stack_driver = CloudStackUtility(ini_data)
    poll_stack = not ini_data.get('no_poll', False)
    if stack_driver.upsert():
        logger.info('stack create/update was started successfully.')

        if poll_stack:
            stack_tool = None
            try:
                profile = ini_data.get('environment', {}).get('profile')
                if profile:
                    boto3_session = boto3.session.Session(profile_name=profile)
                else:
                    boto3_session = boto3.session.Session()

                region = ini_data['environment']['region']
                stack_name = ini_data['environment']['stack_name']

                cf_client = stack_driver.get_cloud_formation_client()

                if not cf_client:
                    cf_client = boto3_session.client('cloudformation', region_name=region)

                stack_tool = stack_tool = StackTool(
                    stack_name,
                    region,
                    cf_client
                )
            except Exception as wtf:
                logger.warning('there was a problems creating stack tool: {}'.format(wtf))

            if stack_driver.poll_stack():
                try:
                    logger.info('stack create/update was finished successfully.')
                    stack_tool.print_stack_info()
                except Exception as wtf:
                    logger.warning('there was a problems printing stack info: {}'.format(wtf))

                sys.exit(0)
            else:
                try:
                    logger.error('stack create/update was did not go well.')
                    stack_tool.print_stack_events()
                except Exception as wtf:
                    logger.warning('there was a problems printing stack events: {}'.format(wtf))
                sys.exit(1)
    else:
        logger.error('start of stack create/update did not go well.')
        sys.exit(1)


def start_list(command_line):
    """
    Facilitate the listing of a CloudFormation stacks

    Args:
        command_line - a dictionary to of info to inform the operation

    Returns:
       True if happy else False
    """
    stack_driver = CloudStackUtility(command_line)
    return stack_driver.list()


def start_smash(command_line):
    """
    Facilitate the smashing of a CloudFormation stack

    Args:
        command_line - a dictionary to of info to inform the operation

    Returns:
       True if happy else False
    """
    stack_driver = CloudStackUtility(command_line)
    return stack_driver.smash()


def find_myself():
    """
    Find myself

    Args:
        None

    Returns:
       An Amazon region
    """
    s = boto3.session.Session()
    return s.region_name


def read_config_info(ini_file):
    """
    Read the INI file

    Args:
        ini_file - path to the file

    Returns:
        A dictionary of stuff from the INI file

    Exits:
        1 - if problems are encountered
    """
    try:
        config = RawConfigParser()
        config.optionxform = lambda option: option
        config.read(ini_file)
        the_stuff = {}
        for section in config.sections():
            the_stuff[section] = {}
            for option in config.options(section):
                the_stuff[section][option] = config.get(section, option)

        return the_stuff
    except Exception as wtf:
        logger.error('Exception caught in read_config_info(): {}'.format(wtf))
        traceback.print_exc(file=sys.stdout)
        return sys.exit(1)
