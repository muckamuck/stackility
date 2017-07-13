"""
The command line interface to stackility.

Major help from: https://www.youtube.com/watch?v=kNke39OZ2k0
"""
from stackility import CloudStackUtility
import click
import json
import boto3
import logging
import sys


@click.group()
@click.version_option(version='0.1')
def cli():
    pass


@cli.command()
@click.option('--version', '-v', help='code version', required=True)
@click.option('--tags', '-g', help='tags file, key/valye pairs', type=click.File('rb'), required=True)
@click.option('--properties', '-p', help='properties file to inject into stack parameters', type=click.File('rb'), required=True)
@click.option('--template', '-t', help='template file', type=click.File('rb'), required=True)
@click.option('--region', '-r', help='AWS region')
@click.option('--bucket', '-b', help='bucket for stuff', required=True)
@click.option('--profile', '-f', help='AWS CLI profile')
@click.option('--name', '-n', help='stack_name', required=True)
@click.option('--dryrun', '-d', help='dry run', is_flag=True)
@click.option('--yaml', '-y', help='YAML template', is_flag=True)
def upsert(version, tags, properties, template, region, bucket, profile, name, dryrun, yaml):
    command_line = {}
    command_line['stackName'] = name
    command_line['destinationBucket'] = bucket
    command_line['templateFile'] = template.name
    command_line['tagFile'] = tags.name
    command_line['parameterFile'] = properties.name
    command_line['codeVersion'] = version

    if profile:
        command_line['profile'] = profile

    if region:
        command_line['region'] = region
    else:
        command_line['region'] = find_myself()

    if yaml:
        command_line['yaml'] = True
    else:
        command_line['yaml'] = False

    if dryrun:
        command_line['dryrun'] = True
    else:
        command_line['dryrun'] = False

    print(json.dumps(command_line, indent=2))
    start_work(command_line)


@cli.command()
@click.option('-s', '--stack', required=True)
def delete(stack):
    click.echo('delete called: {}'.format(stack))


def start_work(command_line):
    stack_driver = CloudStackUtility(command_line)
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


def find_myself():
    s = boto3.session.Session()
    return s.region_name
