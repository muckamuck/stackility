"""
The command line interface to stackility.

Major help from: https://www.youtube.com/watch?v=kNke39OZ2k0
"""
from stackility import CloudStackUtility
from stack_tool import StackTool
import ConfigParser
import click
import time
import json
import boto3
import logging
import sys
import os
import traceback


@click.group()
@click.version_option(version='0.5.1')
def cli():
    pass


@cli.command()
@click.option('--version', '-v', help='code version')
@click.option('--stack', '-s', help='stack name')
@click.option('--ini', '-i', help='INI file with needed information', required=True)
@click.option('--dryrun', '-d', help='dry run', is_flag=True)
@click.option('--yaml', '-y', help='YAML template (deprecated - YAMLness is now detected at run-time', is_flag=True)
@click.option('--no-poll', help='Start the stack work but do not poll', is_flag=True)
@click.option('--work-directory', '-w', help='Start in the given working directory')
def upsert(version, stack, ini, dryrun, yaml, no_poll, work_directory):
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

    if yaml:
        ini_data['yaml'] = True
    else:
        ini_data['yaml'] = False

    if no_poll:
        ini_data['no_poll'] = True
    else:
        ini_data['no_poll'] = False

    if dryrun:
        ini_data['dryrun'] = True
    else:
        ini_data['dryrun'] = False

    if stack:
        ini_data['environment']['stack_name'] = stack

    if work_directory:
        try:
            os.chdir(work_directory)
        except Exception as wtf:
            logging.error(wtf)
            sys.exit(2)

    print(json.dumps(ini_data, indent=2))
    start_upsert(ini_data)


@cli.command()
@click.option('-s', '--stack', required=True)
@click.option('-r', '--region')
@click.option('-f', '--profile')
def delete(stack, region, profile):
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


def start_upsert(ini_data):
    stack_driver = CloudStackUtility(ini_data)
    poll_stack = not ini_data.get('no_poll', False)
    if stack_driver.upsert():
        logging.info('stack create/update was started successfully.')

        if poll_stack:
            if stack_driver.poll_stack():
                logging.info('stack create/update was finished successfully.')
                try:
                    profile = ini_data.get('environment', {}).get('profile')
                    if profile:
                        b3Sess = boto3.session.Session(profile_name=profile)
                    else:
                        b3Sess = boto3.session.Session()

                    region = ini_data['environment']['region']
                    stack_name = ini_data['environment']['stack_name']
                    cf_client = b3Sess.client('cloudformation', region_name=region)
                    stack_tool = stack_tool = StackTool(
                        stack_name,
                        region,
                        cf_client
                    )
                    stack_tool.print_stack_info()
                except Exception as wtf:
                    logging.warning('there was a problems printing stack info: {}'.format(wtf))

                sys.exit(0)
            else:
                logging.error('stack create/update was did not go well.')
                sys.exit(1)
    else:
        logging.error('start of stack create/update did not go well.')
        sys.exit(1)


def start_list(command_line):
    stack_driver = CloudStackUtility(command_line)
    return stack_driver.list()


def start_smash(command_line):
    stack_driver = CloudStackUtility(command_line)
    return stack_driver.smash()


def find_myself():
    s = boto3.session.Session()
    return s.region_name


def read_config_info(ini_file):
    try:
        config = ConfigParser.RawConfigParser()
        config.optionxform = lambda option: option
        config.read(ini_file)
        the_stuff = {}
        for section in config.sections():
            the_stuff[section] = {}
            for option in config.options(section):
                the_stuff[section][option] = config.get(section, option)

        return the_stuff
    except Exception as wtf:
        logging.error('Exception caught in read_config_info(): {}'.format(wtf))
        traceback.print_exc(file=sys.stdout)
        return sys.exit(1)


def validate_config_info():
    return True
