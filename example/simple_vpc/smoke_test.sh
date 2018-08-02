#!/bin/bash
set -e
log_file="/tmp/smoke_test_$(date +%s).log"
echo "Loading SSM parameters" 2>&1 | tee -a ${log_file}
aws ssm  put-parameter --value 1.0 --name foo_version --type SecureString --overwrite --region us-west-2
aws ssm  put-parameter --value 42 --name answer --type SecureString --overwrite --region us-west-2

(
    echo " "; \
    echo "Testing regular YAML template"; \
    cd yaml; \
    stackility upsert -i example.ini; \
    echo " "; \
    echo "Regular YAML template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Testing short form YAML template"; \
    cd short_form_yaml; \
    stackility upsert -i example.ini; \
    echo " "; \
    echo "Short form YAML template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Testing JSON template"; \
    cd short_form_yaml; \
    stackility upsert -i example.ini; \
    echo " "; \
    echo "JSON template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Smoke test:"; \
    echo "The term originates in hardware repair and has been applied to software. It's"; \
    echo "intended to be a quick test to see if the application \"catches on fire\" when"; \
    echo "run for the first time. As stated above it's just to make sure you don't waste"; \
    echo "a bunch of folks time by setting them loose on something that's obviously"; \
    echo "broken."; \
) 2>&1 | tee -a ${log_file}
