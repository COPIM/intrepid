#!/bin/bash
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i ./ansible/hosts.cfg ./ansible/server_setup.yml