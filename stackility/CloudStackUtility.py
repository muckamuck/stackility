import boto3
import logging
import sys
import os
import time
import json
import yaml
import traceback

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


try:
    POLL_INTERVAL = os.environ.get('CSU_POLL_INTERVAL', 30)
except:
    POLL_INTERVAL = 30

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
                    datefmt='%Y/%m/%d-%H:%M:%S')

logging.getLogger().setLevel(logging.INFO)


class CloudStackUtility:
    """
    Cloud stack utility is yet another tool create AWS Cloudformation stacks.
    """
    _b3Sess = None
    _cloudFormation = None
    _config = None
    _parameters = {}
    _stackParameters = []
    _s3 = None
    _tags = []
    _templateUrl = None
    _updateStack = False

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
        self._initialize_upsert()

        required_parameters = []
        self._stackParameters = []

        try:
            available_parameters = self._parameters.keys()
            if self._config.get('yaml'):
                with open(self._config.get('templateFile'), 'r') as f:
                    template = yaml.load(f, Loader=Loader)
            else:
                json_stuff = open(self._config.get('templateFile'))
                template = json.load(json_stuff)

            for parameter_name in template['Parameters']:
                required_parameters.append(str(parameter_name))

            logging.info(' required parameters: ' + str(required_parameters))
            logging.info('available parameters: ' + str(available_parameters))

            parameters = []
            for required_parameter in required_parameters:
                parameter = {}
                parameter['ParameterKey'] = str(required_parameter)
                parameter['ParameterValue'] = self._parameters[str(required_parameter)]
                parameters.append(parameter)

            if self._config.get('dryrun', False):
                logging.info('This was a dryrun')
                sys.exit(0)

            if self._updateStack:
                self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
                self._tags.append({"Key": "ANSWER", "Value": str(42)})
                stack = self._cloudFormation.update_stack(
                    StackName=self._config.get('stackName'),
                    TemplateURL=self._templateUrl,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                    Tags=self._tags
                )
            else:
                self._tags.append({"Key": "CODE_VERSION_SD", "Value": self._config.get('codeVersion')})
                self._tags.append({"Key": "ANSWER", "Value": str(42)})
                stack = self._cloudFormation.create_stack(
                    StackName=self._config.get('stackName'),
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
            traceback.print_exc(file=sys.stdout)

            return False

        return True

    def list(self):
        """
        List the existing stacks in the indicated region

        Args:
            None

        Returns:
            True if the stack create/update is started successfully else
            False if the start goes off in the weeds.

        Exits:
            If the user asked for a dryrun exit(with a code 0) the thing here. There is no
            point continuing after that point.

        """
        self._initialize_list()
        interested = True

        response = self._cloudFormation.list_stacks()
        while interested:
            if 'StackSummaries' in response:
                for stack in response['StackSummaries']:
                    stack_status = stack['StackStatus']
                    if stack_status != 'DELETE_COMPLETE':
                        print('Stack: {} - [{}]'.format(stack['StackName'], stack['StackStatus']))

            next_token = response.get('NextToken', None)
            if next_token:
                response = self._cloudFormation.list_stacks(NextToken=next_token)
            else:
                interested = False

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
            if self._config.get('profile'):
                self._b3Sess = boto3.session.Session(profile_name=self._config.get('profile'))
            else:
                self._b3Sess = boto3.session.Session()

            self._s3 = self._b3Sess.client('s3')
            self._cloudFormation = self._b3Sess.client('cloudformation', region_name=self._config.get('region'))
            return True
        except Exception as wtf:
            logging.error('Exception caught in intialize_session(): {}'.format(wtf))
            traceback.print_exc(file=sys.stdout)
            return False

    def _fill_parameters(self):
        """
        Fill in the _parameters dict from the properties file.

        Args:
            None

        Returns:
            True

        Todo:
            Figure what could go wrong and at least acknowledge the
            the fact that Murphy was an optimist.
        """
        with open(self._config.get('parameterFile')) as f:
            wrk = f.readline()
            while wrk:
                wrk = wrk.rstrip()
                key_val = wrk.split('=')
                if len(key_val) == 2:
                    self._parameters[key_val[0]] = key_val[1]

                wrk = f.readline()

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
        with open(self._config.get('tagFile')) as f:
            wrk = f.readline()
            while wrk:
                tag = {}
                wrk = wrk.rstrip()
                key_val = wrk.split('=')
                if len(key_val) == 2:
                    tag['Key'] = key_val[0]
                    tag['Value'] = key_val[1]
                    self._tags.append(tag)

                wrk = f.readline()

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
            response = self._cloudFormation.describe_stacks(StackName=self._config.get('stackName'))
            stack = response['Stacks'][0]
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

            if not os.path.isfile(self._config.get('templateFile')):
                logging.info(self._config.get('templateFile') + " not actually a file")
                return False

            logging.info("Copying " +
                         self._config.get('parameterFile') +
                         " to " + "s3://" +
                         self._config.get('destinationBucket') +
                         "/" +
                         propertyfile_key)

            self._s3.upload_file(self._config.get('parameterFile'),
                                 self._config.get('destinationBucket'),
                                 propertyfile_key)

            logging.info("Copying " +
                         self._config.get('templateFile') +
                         " to " + "s3://" +
                         self._config.get('destinationBucket') +
                         "/" + stackfile_key)

            self._s3.upload_file(self._config.get('templateFile'),
                                 self._config.get('destinationBucket'),
                                 stackfile_key)

            self._templateUrl = 'https://s3.amazonaws.com/' + \
                self._config.get('destinationBucket') + \
                '/' + \
                stackfile_key

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
            stack_name=self._config.get('stackName'),
            version=self._config.get('codeVersion')
        )

        stub = stub + "/" + str(now.tm_year)
        stub = stub + "/" + str('%02d' % now.tm_mon)
        stub = stub + "/" + str('%02d' % now.tm_mday)
        stub = stub + "/" + str('%02d' % now.tm_hour)
        stub = stub + ":" + str('%02d' % now.tm_min)
        stub = stub + ":" + str('%02d' % now.tm_sec)

        if self._config.get('yaml'):
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
        while True:
            try:
                response = self._cloudFormation.describe_stacks(StackName=self._config.get('stackName'))
                stack = response['Stacks'][0]
                current_status = stack['StackStatus']
                logging.info('Current status of ' + self._config.get('stackName') + ': ' + current_status)
                if current_status.endswith('COMPLETE') or current_status.endswith('FAILED'):
                    if current_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                        return True
                    else:
                        return False

                time.sleep(POLL_INTERVAL)
            except Exception as wtf:
                logging.error('Exception caught in wait_for_stack(): {}'.format(wtf))
                traceback.print_exc(file=sys.stdout)
                return False

    def _initialize_list(self):
        if not self._init_boto3_clients():
            logging.error('session initialization was not good')
            raise SystemError

    def _initialize_upsert(self):
        if not self._init_boto3_clients():
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
