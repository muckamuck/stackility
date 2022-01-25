'''
The main class for the Stackility adventure.
'''
# pylint: disable=broad-except
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=logging-format-interpolation

import boto3
from botocore.exceptions import ClientError
from cloudformation_validator.ValidateUtility import ValidateUtility
from bson import json_util
import jinja2
import getpass
import logging
import tempfile
import sys
import os
import time
import json
import yaml
import traceback
import uuid
import requests


try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def default_ctor(loader, tag_suffix, node):
    '''
    Some extra bits to use the short form of intrinsic functions in YAML templates.
    '''
    return tag_suffix + ' ' + str(node.value)


try:
    POLL_INTERVAL = int(os.environ.get('CSU_POLL_INTERVAL', 30))
except:
    POLL_INTERVAL = 30

logger = logging.getLogger(__name__)

deletable_states = [
    'REVIEW_IN_PROGRESS',
    'ROLLBACK_COMPLETE'
]

complete_states = [
    'CREATE_COMPLETE',
    'UPDATE_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE'
]


class CloudStackUtility:
    """
    Cloud stack utility is yet another tool create AWS Cloudformation stacks.
    """
    ASK = '[ask]'
    SSM = '[ssm:'
    _verbose = False
    _template = None
    _b3Sess = None
    _cloudFormation = None
    _config = None
    _parameters = {}
    _stackParameters = []
    _s3 = None
    _ssm = None
    _tags = []
    _templateUrl = None
    _updateStack = False
    _yaml = False

    def __init__(self, config_block):
        """
        Cloud stack utility init method.

        Args:
            config_block - a dictionary creates from the CLI driver. See that
                           script for the things that are required and
                           optional.

        Returns:
           not a damn thing

        Raises:
            SystemError - if everything isn't just right
        """
        if config_block:
            self._config = config_block
        else:
            logger.error('config block was garbage')
            raise SystemError

    def upsert(self):
        """
        The main event of the utility. Create or update a Cloud Formation
        stack. Injecting properties where needed

        Args:
            None

        Returns:
            True if the stack create/update is started successfully else
            False if the start goes off in the weeds.

        Exits:
            If the user asked for a dryrun exit(with a code 0) the thing here. There is no
            point continuing after that point.

        """

        required_parameters = []
        self._stackParameters = []

        try:
            self._initialize_upsert()
        except Exception:
            return False

        try:
            available_parameters = self._parameters.keys()

            for parameter_name in self._template.get('Parameters', {}):
                required_parameters.append(str(parameter_name))

            logger.info(' required parameters: ' + str(required_parameters))
            logger.info('available parameters: ' + str(available_parameters))

            parameters = []
            for required_parameter in required_parameters:
                parameter = {}
                parameter['ParameterKey'] = str(required_parameter)

                required_parameter = str(required_parameter)
                if required_parameter in self._parameters:
                    parameter['ParameterValue'] = self._parameters[required_parameter]
                else:
                    parameter['ParameterValue'] = self._parameters[required_parameter.lower()]

                parameters.append(parameter)

            if not self._analyze_stuff():
                sys.exit(1)

            if self._config.get('dryrun', False):
                logger.info('Generating change set')
                set_id = self._generate_change_set(parameters)
                if set_id:
                    self._describe_change_set(set_id)

                logger.info('This was a dryrun')
                sys.exit(0)

            self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
            self._tags.append({"Key": "ANSWER", "Value": str(42)})
            if self._updateStack:
                stack = self._cloudFormation.update_stack(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
                    Tags=self._tags,
                    ClientRequestToken=str(uuid.uuid4())
                )
                logger.info('existing stack ID: {}'.format(stack.get('StackId', 'unknown')))
            else:
                stack = self._cloudFormation.create_stack(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
                    Tags=self._tags,
                    ClientRequestToken=str(uuid.uuid4())
                )
                logger.info('new stack ID: {}'.format(stack.get('StackId', 'unknown')))
        except Exception as x:
            if self._verbose:
                logger.error(x, exc_info=True)
            else:
                logger.error(x, exc_info=False)

            return False

        return True

    def _describe_change_set(self, set_id):
        complete_states = ['CREATE_COMPLETE', 'FAILED', 'UNKNOWN']
        try:
            logger.info('polling change set, POLL_INTERVAL={}'.format(POLL_INTERVAL))
            response = self._cloudFormation.describe_change_set(ChangeSetName=set_id)
            status = response.get('Status', 'UNKNOWN')
            while status not in complete_states:
                logger.info('current set status: {}'.format(status))
                time.sleep(POLL_INTERVAL)
                response = self._cloudFormation.describe_change_set(ChangeSetName=set_id)
                status = response.get('Status', 'UNKNOWN')

            logger.info('current set status: {}'.format(status))
            print('\n')
            print('Change set report:')
            for change in response.get('Changes', []):
                print(
                    json.dumps(
                        change,
                        indent=2,
                        default=json_util.default
                    )
                )
                print('\n')

            logger.info('cleaning up change set')
            self._cloudFormation.delete_change_set(ChangeSetName=set_id)
            return True
        except Exception as ruh_roh_shaggy:
            if self._verbose:
                logger.error(ruh_roh_shaggy, exc_info=True)
            else:
                logger.error(ruh_roh_shaggy, exc_info=False)

        return False

    def _generate_change_set(self, parameters):
        try:
            self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
            self._tags.append({"Key": "ANSWER", "Value": str(42)})
            set_name = 'chg{}'.format(int(time.time()))
            if self._updateStack:
                changes = self._cloudFormation.create_change_set(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
                    Tags=self._tags,
                    ChangeSetName=set_name,
                    ChangeSetType='UPDATE'
                )
            else:
                changes = self._cloudFormation.create_change_set(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
                    Tags=self._tags,
                    ChangeSetName=set_name,
                    ChangeSetType='CREATE'
                )
            if self._verbose:
                logger.info('Change set: {}'.format(
                    json.dumps(changes, indent=2, default=json_util.default)
                ))

            return changes.get('Id', None)
        except Exception as ruh_roh_shaggy:
            if self._verbose:
                logger.error(ruh_roh_shaggy, exc_info=True)
            else:
                logger.error(ruh_roh_shaggy, exc_info=False)

        return None

    def _render_template(self):
        buf = None

        try:
            context = self._config.get('meta-parameters', None)
            if not context:
                return True

            template_file = self._config.get('environment', {}).get('template', None)
            path, filename = os.path.split(template_file)
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(path or './')
            )

            buf = env.get_template(filename).render(context)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rdr', delete=False) as tmp:
                tmp.write(buf)
                logger.info('template rendered into {}'.format(tmp.name))
                self._config['environment']['template'] = tmp.name

        except Exception as wtf:
            print('error: _render_template() caught {}'.format(wtf))
            sys.exit(1)

        return buf

    def _load_template(self):
        template_decoded = False
        template_file = self._config.get('environment', {}).get('template', None)
        self._template = None

        try:
            json_stuff = open(template_file)
            self._template = json.load(json_stuff)

            if self._template and 'Resources' in self._template:
                template_decoded = True
                self._yaml = False
                logger.info('template is JSON')
            else:
                logger.info('template is not a valid JSON template')
        except Exception as x:
            template_decoded = False
            logger.debug('Exception caught in load_template(json): {}'.format(x))
            logger.info('template is not JSON')

        if not template_decoded:
            try:
                yaml.add_multi_constructor('', default_ctor, Loader=Loader)
                with open(template_file, 'r') as f:
                    self._template = yaml.load(f, Loader=Loader)

                if self._template and 'Resources' in self._template:
                    template_decoded = True
                    self._yaml = True
                    logger.info('template is YAML')
                else:
                    logger.info('template is not a valid YAML template')
            except Exception as x:
                template_decoded = False
                logger.debug('Exception caught in load_template(yaml): {}'.format(x))
                logger.info('template is not YAML')

        return template_decoded

    def list(self):
        """
        List the existing stacks in the indicated region

        Args:
            None

        Returns:
            True if True

        Todo:
            Figure out what could go wrong and take steps
            to hanlde problems.
        """
        self._initialize_list()
        interested = True

        response = self._cloudFormation.list_stacks()
        print('Stack(s):')
        while interested:
            if 'StackSummaries' in response:
                for stack in response['StackSummaries']:
                    stack_status = stack['StackStatus']
                    if stack_status != 'DELETE_COMPLETE':
                        print('    [{}] - {}'.format(stack['StackStatus'], stack['StackName']))

            next_token = response.get('NextToken', None)
            if next_token:
                response = self._cloudFormation.list_stacks(NextToken=next_token)
            else:
                interested = False

        return True

    def smash(self):
        """
        Smash the given stack

        Args:
            None

        Returns:
            True if True

        Todo:
            Figure out what could go wrong and take steps
            to hanlde problems.
        """
        self._initialize_smash()
        try:
            stack_name = self._config.get('environment', {}).get('stack_name', None)
            response = self._cloudFormation.describe_stacks(StackName=stack_name)
            logger.debug('smash pre-flight returned: {}'.format(
                json.dumps(response,
                           indent=4,
                           default=json_util.default
                           )))
        except ClientError as wtf:
            logger.warning('your stack is in another castle [0].')
            return False
        except Exception as wtf:
            logger.error('failed to find intial status of smash candidate: {}'.format(wtf))
            return False

        response = self._cloudFormation.delete_stack(StackName=stack_name)
        logger.info('delete started for stack: {}'.format(stack_name))
        logger.debug('delete_stack returned: {}'.format(json.dumps(response, indent=4)))
        return self.poll_stack()

    def _init_boto3_clients(self):
        """
        The utililty requires boto3 clients to Cloud Formation and S3. Here is
        where we make them.

        Args:
            None

        Returns:
            Good or Bad; True or False
        """
        try:
            profile = self._config.get('environment', {}).get('profile')
            region = self._config.get('environment', {}).get('region')
            if profile:
                self._b3Sess = boto3.session.Session(profile_name=profile)
            else:
                self._b3Sess = boto3.session.Session()

            self._s3 = self._b3Sess.client('s3')
            self._cloudFormation = self._b3Sess.client('cloudformation', region_name=region)
            self._ssm = self._b3Sess.client('ssm', region_name=region)

            return True
        except Exception as wtf:
            logger.error('Exception caught in intialize_session(): {}'.format(wtf))
            traceback.print_exc(file=sys.stdout)
            return False

    def _fill_defaults(self):
        try:
            parms = self._template['Parameters']
            for key in parms:
                key = str(key)
                if 'Default' in parms[key] and key not in self._parameters:
                    self._parameters[key] = str(parms[key]['Default'])

        except Exception as wtf:
            logger.error('Exception caught in fill_defaults(): {}'.format(wtf))
            traceback.print_exc(file=sys.stdout)
            return False

        return True

    def _get_ssm_parameter(self, p):
        """
        Get parameters from Simple Systems Manager

        Args:
            p - a parameter name

        Returns:
            a value, decrypted if needed, if successful or None if things go
            sideways.
        """
        try:
            response = self._ssm.get_parameter(Name=p, WithDecryption=True)
            return response.get('Parameter', {}).get('Value', None)
        except Exception as ruh_roh:
            logger.error(ruh_roh, exc_info=False)

        return None

    def _fill_parameters(self):
        """
        Fill in the _parameters dict from the properties file.

        Args:
            None

        Returns:
            True

        Todo:
            Figure out what could go wrong and at least acknowledge the the
            fact that Murphy was an optimist.
        """
        self._parameters = self._config.get('parameters', {})
        self._fill_defaults()

        for k in self._parameters.keys():
            try:
                if self._parameters[k].startswith(self.SSM) and self._parameters[k].endswith(']'):
                    parts = self._parameters[k].split(':')
                    tmp = parts[1].replace(']', '')
                    val = self._get_ssm_parameter(tmp)
                    if val:
                        self._parameters[k] = val
                    else:
                        logger.error('SSM parameter {} not found'.format(tmp))
                        return False
                elif self._parameters[k] == self.ASK:
                    val = None
                    a1 = '__x___'
                    a2 = '__y___'
                    prompt1 = "Enter value for '{}': ".format(k)
                    prompt2 = "Confirm value for '{}': ".format(k)
                    while a1 != a2:
                        a1 = getpass.getpass(prompt=prompt1)
                        a2 = getpass.getpass(prompt=prompt2)
                        if a1 == a2:
                            val = a1
                        else:
                            print('values do not match, try again')
                    self._parameters[k] = val
            except:
                pass

        return True

    def _read_tags(self):
        """
        Fill in the _tags dict from the tags file.

        Args:
            None

        Returns:
            True

        Todo:
            Figure what could go wrong and at least acknowledge the
            the fact that Murphy was an optimist.
        """
        tags = self._config.get('tags', {})
        logger.info('Tags:')
        for tag_name in tags.keys():
            tag = {}
            tag['Key'] = tag_name
            tag['Value'] = tags[tag_name]
            self._tags.append(tag)
            logger.info('{} = {}'.format(tag_name, tags[tag_name]))

        logger.debug(json.dumps(
            self._tags,
            indent=2,
            sort_keys=True
        ))
        return True

    def _set_update(self):
        """
        Determine if we are creating a new stack or updating and existing one.
        The update member is set as you would expect at the end of this query.

        Args:
            None

        Returns:
            True
        """
        try:
            self._updateStack = False
            stack_name = self._config.get('environment', {}).get('stack_name', None)
            response = self._cloudFormation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            stack_status = stack.get('StackStatus')
            if stack_status in deletable_states:
                logger.info('stack is in {} and should be deleted'.format(stack_status))
                del_stack_resp = self._cloudFormation.delete_stack(StackName=stack_name)
                logger.info('delete started for stack: {}'.format(stack_name))
                logger.debug('delete_stack returned: {}'.format(json.dumps(del_stack_resp, indent=4)))
                stack_delete = self.poll_stack()
                if not stack_delete:
                    return False

            if stack['StackStatus'] in complete_states:
                self._updateStack = True
        except:
            self._updateStack = False

        logger.info('update_stack: ' + str(self._updateStack))
        return True

    def _archive_elements(self):
        """
        Cloud Formation likes to take the template from S3 so here we put the
        template into S3. We also store the parameters file that was used in
        this run. Note: you can pass anything as the version string but you
        should at least consider a version control tag or git commit hash as
        the version.

        Args:
            None

        Returns:
            True if the stuff lands in S3 or False if the file doesn't
            really exist or the upload goes sideways.
        """
        try:
            stackfile_key, propertyfile_key = self._craft_s3_keys()

            template_file = self._config.get('environment', {}).get('template', None)
            bucket = self._config.get('environment', {}).get('bucket', None)
            if not os.path.isfile(template_file):
                logger.info("{} is not actually a file".format(template_file))
                return False

            logger.info('Copying parameters to s3://{}/{}'.format(bucket, propertyfile_key))
            temp_file_name = '/tmp/{}'.format((str(uuid.uuid4()))[:8])
            with open(temp_file_name, 'w') as dump_file:
                json.dump(self._parameters, dump_file, indent=4)

            self._s3.upload_file(temp_file_name, bucket, propertyfile_key)

            logger.info('Copying {} to s3://{}/{}'.format(template_file, bucket, stackfile_key))
            self._s3.upload_file(template_file, bucket, stackfile_key)

            self._templateUrl = 'https://s3.amazonaws.com/{}/{}'.format(bucket, stackfile_key)
            logger.info("template_url: " + self._templateUrl)
            return True
        except Exception as x:
            logger.error('Exception caught in copy_stuff_to_S3(): {}'.format(x))
            traceback.print_exc(file=sys.stdout)
            return False

    def _craft_s3_keys(self):
        """
        We are putting stuff into S3, were supplied the bucket. Here we
        craft the key of the elements we are putting up there in the
        internet clouds.

        Args:
            None

        Returns:
            a tuple of teplate file key and property file key
        """
        now = time.gmtime()
        stub = "templates/{stack_name}/{version}".format(
            stack_name=self._config.get('environment', {}).get('stack_name', None),
            version=self._config.get('codeVersion')
        )

        stub = stub + "/" + str(now.tm_year)
        stub = stub + "/" + str('%02d' % now.tm_mon)
        stub = stub + "/" + str('%02d' % now.tm_mday)
        stub = stub + "/" + str('%02d' % now.tm_hour)
        stub = stub + ":" + str('%02d' % now.tm_min)
        stub = stub + ":" + str('%02d' % now.tm_sec)

        if self._yaml:
            template_key = stub + "/stack.yaml"
        else:
            template_key = stub + "/stack.json"

        property_key = stub + "/stack.properties"
        return template_key, property_key

    def poll_stack(self):
        """
        Spin in a loop while the Cloud Formation process either fails or succeeds

        Args:
            None

        Returns:
            Good or bad; True or False
        """
        logger.info('polling stack status, POLL_INTERVAL={}'.format(POLL_INTERVAL))
        time.sleep(POLL_INTERVAL)
        completed_states = [
            'CREATE_COMPLETE',
            'UPDATE_COMPLETE',
            'DELETE_COMPLETE'
        ]
        stack_name = self._config.get('environment', {}).get('stack_name', None)
        while True:
            try:
                response = self._cloudFormation.describe_stacks(StackName=stack_name)
                stack = response['Stacks'][0]
                current_status = stack['StackStatus']
                logger.info('current status of {}: {}'.format(stack_name, current_status))
                if current_status.endswith('COMPLETE') or current_status.endswith('FAILED'):
                    if current_status in completed_states:
                        return True
                    else:
                        return False

                time.sleep(POLL_INTERVAL)
            except ClientError as wtf:
                if str(wtf).find('does not exist') == -1:
                    logger.error('Exception caught in wait_for_stack(): {}'.format(wtf))
                    traceback.print_exc(file=sys.stdout)
                    return False
                else:
                    logger.info('{} is gone'.format(stack_name))
                    return True
            except Exception as wtf:
                logger.error('Exception caught in wait_for_stack(): {}'.format(wtf))
                traceback.print_exc(file=sys.stdout)
                return False

    def _initialize_list(self):
        if not self._init_boto3_clients():
            logger.error('session initialization was not good')
            raise SystemError

    def _initialize_smash(self):
        if not self._init_boto3_clients():
            logger.error('session initialization was not good')
            raise SystemError

    def _validate_ini_data(self):
        if 'stack_name' not in self._config.get('environment', {}):
            return False
        elif 'bucket' not in self._config.get('environment', {}):
            return False
        elif 'template' not in self._config.get('environment', {}):
            return False
        else:
            template_file = self._config.get('environment', {}).get('template', None)
            if os.path.isfile(template_file):
                return True
            else:
                logger.error('template file \'{}\' does not exist, I give up!'.format(template_file))
                return False

    def _initialize_upsert(self):
        if not self._validate_ini_data():
            logger.error('INI file missing required bits; bucket and/or template and/or stack_name')
            raise SystemError
        elif not self._render_template():
            logger.error('template rendering failed')
            raise SystemError
        elif not self._load_template():
            logger.error('template initialization was not good')
            raise SystemError
        elif not self._init_boto3_clients():
            logger.error('session initialization was not good')
            raise SystemError
        elif not self._fill_parameters():
            logger.error('parameter setup was not good')
            raise SystemError
        elif not self._read_tags():
            logger.error('tags initialization was not good')
            raise SystemError
        elif not self._archive_elements():
            logger.error('saving stuff to S3 did not go well')
            raise SystemError
        elif not self._set_update():
            logger.error('there was a problem determining update or create')
            raise SystemError

    def _analyze_stuff(self):
        template_scanner = self._config.get('analysis', {}).get('template', None)
        tags_scanner = self._config.get('analysis', {}).get('tags', None)

        if template_scanner or tags_scanner:
            r = self._externally_analyze_stuff(template_scanner, tags_scanner)
            if not r:
                return False

        wrk = self._config.get('analysis', {}).get('enforced', 'crap').lower()
        rule_exceptions = self._config.get('analysis', {}).get('exceptions', None)
        if wrk == 'true' or wrk == 'false':
            enforced = wrk == 'true'
            self._internally_analyze_stuff(enforced, rule_exceptions)

        return True

    def _externally_analyze_stuff(self, template_scanner, tags_scanner):
        scans_executed = False
        tags_scan_status = 0
        template_scan_status = 0
        the_data = None

        try:
            if template_scanner:
                scans_executed = True
                with open(self._config['environment']['template'], 'rb') as template_data:
                    the_data = template_data.read()

                r = requests.post(template_scanner, data=the_data)
                answer = json.loads(r.content)
                template_scan_status = answer.get('exit_status', -2)
                print('\nTemplate scan:')
                print(json.dumps(answer, indent=2))

            if tags_scanner:
                scans_executed = True
                with open(self._config['environment']['template'], 'rb') as template_data:
                    the_data = template_data.read()

                r = requests.post(template_scanner, data=the_data)
                answer = json.loads(r.content)
                tags_scan_status = answer.get('exit_status', -2)
                print('\nTag scan:')
                print(json.dumps(answer, indent=2))

            if not scans_executed:
                return True
            elif template_scan_status == 0 and tags_scan_status == 0:
                print('All scans successful')
                return True
            else:
                print('Failed scans')
                return False
        except Exception as wtf:
            print('')
            logger.info('template_scanner: {}'.format(template_scanner))
            logger.info('    tags_scanner: {}'.format(tags_scanner))
            print('')
            logger.error('Exception caught in analyze_stuff(): {}'.format(wtf))
            traceback.print_exc(file=sys.stdout)

        return False

    def _internally_analyze_stuff(self, enforced, rule_exceptions):
        try:
            config_dict = {}
            config_dict['template_file'] = self._config['environment']['template']
            validator = ValidateUtility(config_dict)
            _results = validator.validate()
            results = json.loads(_results)

            for result in results:
                try:
                    error_count = int(result.get('failure_count', 0))
                except Exception as strangeness:
                    logger.warn('internally_analyze_stuff() strangeness: {}'.format(strangeness))
                    error_count = -1
                    if enforced:
                        traceback.print_exc(file=sys.stdout)
                        sys.exit(1)

                if error_count == 0:
                    logger.info('CloudFormation Validator found zero errors')
                elif error_count == 1:
                    if enforced:
                        logger.error('CloudFormation Validator found one error')
                        sys.exit(1)
                    else:
                        logger.warn('CloudFormation Validator found one error')
                elif error_count > 1:
                    if enforced:
                        logger.error(
                            'CloudFormation Validator found {} errors'.format(error_count)
                        )
                        sys.exit(1)
                    else:
                        logger.warn(
                            'CloudFormation Validator found {} errors'.format(error_count)
                        )
        except Exception as ruh_roh_shaggy:
            logger.error('internally_analyze_stuff() exploded: {}'.format(ruh_roh_shaggy))
            traceback.print_exc(file=sys.stdout)
            if enforced:
                sys.exit(1)

        return True

    def get_cloud_formation_client(self):
        return self._cloudFormation
