#!/bin/bash

# We need to get back to the root
cd `dirname ${0}`/../../
stackility upsert \
    -v 1 \
    -g example/simple_vpc/tags.properties \
    -p example/simple_vpc/stack.properties \
    -t example/simple_vpc/template.json \
    -b some-bucket \
    -n Stackility-VPC-Example \
    -r us-east-1
