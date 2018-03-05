import boto3
from botocore.exceptions import ClientError
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


try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


try:
    POLL_INTERVAL = os.environ.get('CSU_POLL_INTERVAL', 30)
except:
    POLL_INTERVAL = 30

logging_level = logging.INFO

logging.basicConfig(
    level=logging_level,
    format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
    datefmt='%Y/%m/%d-%H:%M:%S'
)

logging.getLogger().setLevel(logging_level)


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
            logging.error('config block was garbage')
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

            for parameter_name in self._template['Parameters']:
                required_parameters.append(str(parameter_name))

            logging.info(' required parameters: ' + str(required_parameters))
            logging.info('available parameters: ' + str(available_parameters))

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

            if self._config.get('dryrun', False):
                logging.info('This was a dryrun')
                sys.exit(0)

            if self._updateStack:
                self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
                self._tags.append({"Key": "ANSWER", "Value": str(42)})
                stack = self._cloudFormation.update_stack(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                    Tags=self._tags
                )
            else:
                self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
                self._tags.append({"Key": "ANSWER", "Value": str(42)})
                stack = self._cloudFormation.create_stack(
                    StackName=self._config.get('environment', {}).get('stack_name', None),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                    Tags=self._tags
                )
                logging.info('stack: {}'.format(json.dumps(stack,
                                                           indent=4,
                                                           sort_keys=True)))
        except Exception as x:
            logging.error('Exception caught in upsert(): {}'.format(x))
            if self._verbose:
                traceback.print_exc(file=sys.stdout)

            return False

        return True

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
                logging.info('template rendered into {}'.format(tmp.name))
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
                logging.info('template is JSON')
            else:
                logging.info('template is not a valid JSON template')
        except Exception as x:
            template_decoded = False
            logging.warning('Exception caught in load_template(json): {}'.format(x))
            logging.info('template is not JSON')

        if not template_decoded:
            try:
                with open(template_file, 'r') as f:
                    self._template = yaml.load(f, Loader=Loader)

                if self._template and 'Resources' in self._template:
                    template_decoded = True
                    self._yaml = True
                    logging.info('template is YAML')
                else:
                    logging.info('template is not a valid YAML template')
            except Exception:
                template_decoded = False
                logging.warning('Exception caught in load_template(yaml): {}'.format(x))
                logging.info('template is not YAML')

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
            logging.debug('smash pre-flight returned: {}'.format(
                json.dumps(response,
                           indent=4,
                           default=json_util.default
                           )))
        except ClientError as wtf:
            logging.warning('your stack is in another castle [0].')
            return False
        except Exception as wtf:
            logging.error('failed to find intial status of smash candidate: {}'.format(wtf))
            return False

        response = self._cloudFormation.delete_stack(StackName=stack_name)
        logging.info('delete started for stack: {}'.format(stack_name))
        logging.debug('delete_stack returned: {}'.format(json.dumps(response, indent=4)))
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
            logging.error('Exception caught in intialize_session(): {}'.format(wtf))
            traceback.print_exc(file=sys.stdout)
            return False

    def _fill_defaults(self):
        try:
            parms = self._template['Parameters']
            for key in parms:
                key = str(key)
                if 'Default' in parms[key] and key not in self._parameters:
                    self._parameters[key] = parms[key]['Default']

        except Exception as wtf:
            logging.error('Exception caught in fill_defaults(): {}'.format(wtf))
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
        val = None
        secure_string = False
        try:
            response = self._ssm.describe_parameters(
                Filters=[{'Key': 'Name', 'Values': [p]}]
            )

            if 'Parameters' in response:
                t = response['Parameters'][0].get('Type', None)
                if t == 'String':
                    secure_string = False
                elif t == 'SecureString':
                    secure_string = True

                response = self._ssm.get_parameter(Name=p, WithDecryption=secure_string)
                val = response.get('Parameter', {}).get('Value', None)
        except Exception:
            pass

        return val

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
            if self._parameters[k].startswith(self.SSM) and self._parameters[k].endswith(']'):
                parts = self._parameters[k].split(':')
                tmp = parts[1].replace(']', '')
                val = self._get_ssm_parameter(tmp)
                if val:
                    self._parameters[k] = val
                else:
                    logging.error('SSM parameter {} not found'.format(tmp))
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
        for tag_name in tags.keys():
            tag = {}
            tag['Key'] = tag_name
            tag['Value'] = tags[tag_name]
            self._tags.append(tag)

        logging.info('Tags: {}'.format(json.dumps(
            self._tags,
            indent=4,
            sort_keys=True
        )))
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
            if stack['StackStatus'] == 'ROLLBACK_COMPLETE':
                logging.info('stack is in ROLLBACK_COMPLETE status and should be deleted')
                del_stack_resp = self._cloudFormation.delete_stack(StackName=stack_name)
                logging.info('delete started for stack: {}'.format(stack_name))
                logging.debug('delete_stack returned: {}'.format(json.dumps(del_stack_resp, indent=4)))
                stack_delete = self.poll_stack()
                if not stack_delete:
                    return False

            if stack['StackStatus'] in ['CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']:
                self._updateStack = True
        except:
            self._updateStack = False

        logging.info('update_stack: ' + str(self._updateStack))
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
                logging.info("{} is not actually a file".format(template_file))
                return False

            logging.info('Copying parameters to s3://{}/{}'.format(bucket, propertyfile_key))
            temp_file_name = '/tmp/{}'.format((str(uuid.uuid4()))[:8])
            with open(temp_file_name, 'w') as dump_file:
                json.dump(self._parameters, dump_file, indent=4)

            self._s3.upload_file(temp_file_name, bucket, propertyfile_key)

            logging.info('Copying {} to s3://{}/{}'.format(template_file, bucket, stackfile_key))
            self._s3.upload_file(template_file, bucket, stackfile_key)

            self._templateUrl = 'https://s3.amazonaws.com/{}/{}'.format(bucket, stackfile_key)
            logging.info("template_url: " + self._templateUrl)
            return True
        except Exception as x:
            logging.error('Exception caught in copy_stuff_to_S3(): {}'.format(x))
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
        logging.info('polling stack status, POLL_INTERVAL={}'.format(POLL_INTERVAL))
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
                logging.info('Current status of {}: {}'.format(stack_name, current_status))
                if current_status.endswith('COMPLETE') or current_status.endswith('FAILED'):
                    if current_status in completed_states:
                        return True
                    else:
                        return False

                time.sleep(POLL_INTERVAL)
            except ClientError as wtf:
                if str(wtf).find('does not exist') == -1:
                    logging.error('Exception caught in wait_for_stack(): {}'.format(wtf))
                    traceback.print_exc(file=sys.stdout)
                    return False
                else:
                    logging.info('{} is gone'.format(stack_name))
                    return True
            except Exception as wtf:
                logging.error('Exception caught in wait_for_stack(): {}'.format(wtf))
                traceback.print_exc(file=sys.stdout)
                return False

    def _initialize_list(self):
        if not self._init_boto3_clients():
            logging.error('session initialization was not good')
            raise SystemError

    def _initialize_smash(self):
        if not self._init_boto3_clients():
            logging.error('session initialization was not good')
            raise SystemError

    def _validate_ini_data(self):
        if 'stack_name' not in self._config.get('environment', {}):
            return False
        elif 'bucket' not in self._config.get('environment', {}):
            return False
        elif 'template' not in self._config.get('environment', {}):
            return False
        else:
            return True

    def _initialize_upsert(self):
        if not self._validate_ini_data():
            logging.error('INI file missing required bits; bucket and/or template and/or stack_name')
            raise SystemError
        elif not self._render_template():
            logging.error('template rendering failed')
            raise SystemError
        elif not self._load_template():
            logging.error('template initialization was not good')
            raise SystemError
        elif not self._init_boto3_clients():
            logging.error('session initialization was not good')
            raise SystemError
        elif not self._fill_parameters():
            logging.error('parameter setup was not good')
            raise SystemError
        elif not self._read_tags():
            logging.error('tags initialization was not good')
            raise SystemError
        elif not self._archive_elements():
            logging.error('saving stuff to S3 did not go well')
            raise SystemError
        elif not self._set_update():
            logging.error('there was a problem determining update or create')
            raise SystemError
