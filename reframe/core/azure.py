# Copyright 2016-2022 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import copy
import fnmatch
import functools
import itertools
import json
import jsonschema
import os
import re
import socket
import tempfile

import reframe
import reframe.core.settings as settings
import reframe.utility as util
from reframe.core.environments import normalize_module_list
from reframe.core.exceptions import ConfigError, ReframeFatalError
from reframe.core.logging import getlogger
from reframe.utility import ScopedDict



def check_if_azure_vm():
    print("Checking if this is an azure vm")
    if not os.path.exists('/etc/waagent.conf'):
        return False
    return True

def get_vm_info(systems):
    try:
        # May need to find a better way to do this for clusters on Azure
        # Host names can be quite random
        cmd = "curl -H Metadata:true 'http://169.254.169.254/metadata/instance?api-version=2019-06-04'"
        results = util.osext.run_command(cmd)
        vm_data = json.loads(results.stdout)
        pp_results = json.dumps(vm_data, indent=4)
        pref_idx = vm_data['compute']['vmSize'].find('_')
        vm_size = vm_data['compute']['vmSize'][pref_idx+1:]
        img_ref = vm_data['compute']['storageProfile']['imageReference']
        vm_os = "{}".format(img_ref['offer'].lower())
        vm_os_version = "{}".format(img_ref['sku'].lower())
        vm_image = "{}_{}_{}".format(img_ref['offer'].lower(),
                                       img_ref['sku'].lower(),
                                       img_ref['version'].lower())
        # Read in the json file and search
        tmp_data = re.split('([0-9]+(-[0-9]+)?)',vm_size,1)
        if len(tmp_data) < 4:
            vm_series = "vm_data[vm]['size']"
            print("Tmp data not as expected: {}".format(tmp_data))
        else:
            vm_series = tmp_data[0] + tmp_data[-1]
        #tmp_data = re.split('[0-9]*',vm_size,1)
        #vm_series = "".join(tmp_data)
        vm_series = vm_series.lower()
    
        sysname = "{}".format(vm_series)


        # If on Azure return generated sysname
        getlogger().debug(f'generated azure system {sysname}')

        # Return sysem name and size
    #    print("CWD: {}".format(os.getcwd()))
    #    return (sysname, vm_size)


        for idx,system in enumerate(systems):
            if sysname == system["name"]:
                # Update system variables for the Azure VM
                getlogger().debug(f'idx: {idx}, system {sysname} found in {system}')
                getlogger().debug(f'system {sysname} found in {system}')
                getlogger().debug(f'{systems}')
                getlogger().debug(f'{systems[idx]}')


                # Get information from data file and add it to the vm_data
                vm_data = read_vm_data_file(vm_series, systems[idx]['vm_data_file'], vm_size, vm_os, vm_os_version, vm_image)

                return [ vm_series, vm_size, vm_data ]
            else:
                getlogger().debug(f'Did not find system {sysname} in the config file')
    except Exception as e:
        raise ConfigError(f"\nError {pp_results}"
                          f"\nError {e} "
                          f"for the current system: '{sysname}'.")
    return [ False, False, False ]

def read_vm_data_file(vm_series, vm_data_file, vm_size=None, vm_os=None, vm_os_version=None, vm_image=None):
    vm_data_fp = open(vm_data_file)
    vm_data = {}
    vm_data = json.load(vm_data_fp)
    #print("vm data: {}".format(vm_data))    
    for vm in vm_data.keys():
        if vm_data[vm]['series'] == vm_series.lower() and vm_data[vm]['size'] == vm_size:
            #print("vm {}\tdata: {}".format(vm,vm_data[vm]))    
            vm_data[vm]['vm_series'] = vm_data[vm]['series']
            vm_data[vm]['vm_size'] = vm_size
            vm_data[vm]['vm_os'] = vm_os
            vm_data[vm]['vm_os_version'] = vm_os_version
            vm_data[vm]['vm_image'] = vm_image
            vm_data[vm]['cloud_provider'] = 'azure'
            return(vm_data[vm])
    return({})

