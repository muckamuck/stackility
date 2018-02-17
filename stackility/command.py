"""
The command line interface to stackility.

Major help from: https://www.youtube.com/watch?v=kNke39OZ2k0
"""
from stackility import CloudStackUtility
import ConfigParser
import click
import time
import json
import boto3
import logging
import sys
import traceback


@click.group()
@click.version_option(version='0.4.2')
def cli():
    pass


@cli.command()
@click.option('--version', '-v', help='code version')
@click.option('--stack', '-s', help='stack name')
@click.option('--ini', '-i', help='INI file with needed information', required=True)
@click.option('--dryrun', '-d', help='dry run', is_flag=True)
@click.option('--yaml', '-y', help='YAML template', is_flag=True)
@click.option('--profile', '-f', help='aws profile')
@click.option('--project_dir', '-p', help='project directory')

def upsert(version, stack, ini, dryrun, yaml, profile, project_dir):
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

    if dryrun:
        ini_data['dryrun'] = True
    else:
        ini_data['dryrun'] = False
    if profile:
        ini_data['profile'] = profile
    if project_dir:
        ini_data['project_dir']=project_dir

    if stack:
        ini_data['environment']['stack_name'] = stack

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
    if stack_driver.upsert():
        logging.info('stack create/update was started successfully.')
        if stack_driver.poll_stack():
            logging.info('stack create/update was finished successfully.')
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
        config = ConfigParser.ConfigParser()
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
