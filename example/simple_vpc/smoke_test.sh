#!/bin/bash
echo "Smoke test:" 
echo "The term originates in hardware repair and has been applied to software. It's"
echo "intended to be a quick test to see if the application \"catches on fire\" when"
echo "run for the first time. As stated above it's just to make sure you don't waste"
echo "a bunch of folks time by setting them loose on something that's obviously"
echo "broken."; \
cd $(dirname ${0})

errors_file=$(pwd)/errors_file
cat /dev/null > ${errors_file}

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
    echo "$? - Testing regular YAML template (expect 0)" >> ${errors_file}; \
    echo "Regular YAML template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Testing short form YAML template"; \
    cd short_form_yaml; \
    stackility upsert -i example.ini; \
    echo "$? - Testing short form YAML template (expect 0)" >> ${errors_file}; \
    echo " "; \
    echo "Short form YAML template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Testing JSON template"; \
    cd json; \
    stackility upsert -i example.ini; \
    echo " "; \
    echo "$? - Testing JSON template (expect 0)" >> ${errors_file}; \
    echo "JSON template went well - cleaning up" ; sleep 2; \
    stackility delete -s Stackility-VPC-Example -r us-west-2; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Validating template with warnings"; \
    cd validation_warnings; \
    stackility upsert -i example.ini --dryrun; \
    echo "$? - Validating template with warnings (expect 0)" >> ${errors_file}; \
    echo "Validating template with warnings went well"; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Validating template with errors (not enforced)"; \
    cd validation_errors; \
    stackility upsert -i not_enforced.ini --dryrun; \
    echo "$? - Validating template with errors (expect 0)" >> ${errors_file}; \
) 2>&1 | tee -a ${log_file}

(
    echo " "; \
    echo "Validating template with errors (enforced)"; \
    cd validation_errors; \
    stackility upsert -i enforced.ini --dryrun; \
    echo "$? - Validating template with errors (expect 1)" >> ${errors_file}; \
) 2>&1 | tee -a ${log_file}

echo
echo
echo "================================================================================"
cat ${errors_file}
