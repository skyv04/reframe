# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
# Currently runs only on HB series VMs, will be upgraded to work with N series and HC as well
import os
import json as js
import re

import reframe as rfm
import reframe.utility.sanity as sn
import reframe.utility.udeps as udeps

# rfmdocstart: HPLBenchmar on Single VMs
class GpuCountTestBase(rfm.RunOnlyRegressionTest):
    '''Base class of GPU Count benchmark runtime tests'''

    valid_systems = ['*:gpu']
    valid_prog_environs = ['gnu-azhpc-gpu']
    sourcesdir = None

    # rfmdocstart: set_deps
    @run_after('init')
    def set_dependencies(self):
        self.depends_on('GpuCountPsshInstallTest', udeps.by_env)
    # rfmdocend: set_deps

@rfm.simple_test
class GpuCountAllVMsTest(GpuCountTestBase):
    descr = 'GPU Count ALL VMs test using pdsh'

    # rfmdocstart: set_exec
    @require_deps
    def set_sourcedir(self, GpuCountPsshInstallTest):
        self.sourcesdir = os.path.join(
            GpuCountPsshInstallTest(part='gpu', environ='gnu-azhpc-gpu').stagedir,
            ''
        )
    cmda = "parallel-ssh -p 194 -t 0 -i -h hostlist.txt -O StrictHostKeyChecking=no -O UserKnownHostsFile=/dev/null -O GlobalKnownHostsFile=/dev/null "
    cmdb = "\"sudo lspci | grep \'3D\' | wc -l\" | "
    cmdc = "awk \'$3 == \"[SUCCESS]\" {printf \"VM: %s NGPUs: \", $4 >> \"succeeded_vms.txt\"; getline; print $1 >> \"succeeded_vms.txt\"; getline } $3 == \"[FAILURE]\" {printf \"VM: %s\\n\", $4 >> \"failed_vms.txt\"; getline}\'"
    executable = cmda+cmdb+cmdc
    postrun_cmds = [
        'echo SUCCEEDED:',
        'cat succeeded_vms.txt',
        'echo FAILED:',
        'cat failed_vms.txt',
    ]

    @sanity_function
    def assert_num_succeeded(self):
        num_tests = sn.len(sn.findall(r'VM: (\S+)',
                                         self.stagedir+'/succeeded_vms.txt'))
        num_nodes = sum(1 for _ in open(self.stagedir+'/hostlist.txt'))
        return sn.assert_eq(num_tests, num_nodes)

    @performance_function('GPUs')
    def extract_gpu_s(self, vm='c5e'):
         return sn.extractsingle(rf'VM: {vm} NGPUs: (\S+)',self.stagedir+'/succeeded_vms.txt', 1, float)

    @run_before('performance')
    def set_perf_variables(self):
        '''Build the dictionary with all the performance variables.'''

        self.perf_variables = {}
        with open(self.stagedir+'/succeeded_vms.txt',"r") as f:
            sys_names = f.read()

        systems = re.findall(r"VM:\s(\S+)\s+.*",sys_names,re.M)
        ngpu = re.findall(r"NGPUs: (\S+)",sys_names,re.M)

        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        temp = {vm_series: {}}

        if vm_info != None and 'nhc_values' in vm_info:
            for i in systems:
                temp[vm_series][i] = (vm_info['nhc_values']['gpu_count'],
                                        None,
                                        None,
                                        'GPUs')

        self.reference = temp

        for i in systems:
            self.perf_variables[i] = self.extract_gpu_s(i)

        results = {}
        for i in range(len(systems)):
            results[systems[i]] = ngpu[i]

        with open(self.outputdir+"/gpu_count_test_results.json", "w") as outfile:
            js.dump(results, outfile, indent=4)


@rfm.simple_test
class GpuCountPsshInstallTest(rfm.RunOnlyRegressionTest):
    descr = 'GPU count test: instaling pdsh'
    valid_systems = ['*:gpu']
    valid_prog_environs = ['gnu-azhpc-gpu']
    executable = 'sudo apt install pssh -y'

    @run_after('init')
    def inject_dependencies(self):
        self.depends_on('GpuCountHostListTest', udeps.fully)

    @require_deps
    def set_sourcedir(self, GpuCountHostListTest):
        self.sourcesdir = os.path.join(
            GpuCountHostListTest(part='gpu', environ='gnu-azhpc-gpu').stagedir,
            ''
        )

    @sanity_function
    def validate_install(self):
        return sn.assert_true(os.path.exists('/usr/bin/parallel-ssh'))

@rfm.simple_test
class GpuCountHostListTest(rfm.RunOnlyRegressionTest):
    descr = 'GPU Count building hostlist'
    valid_systems = ['*:gpu']
    valid_prog_environs = ['gnu-azhpc-gpu']
    executable = 'echo $(hostname) > hostlist.txt'
    postrun_cmds = [
        "if command -v pbsnodes --version &> /dev/null; then pbsnodes -avS | grep free | awk -F ' ' '{print $1}' >> hostlist.txt'; fi"  
    ]

    @sanity_function
    def validate_download(self):
        return sn.assert_true(os.path.exists('hostlist.txt'))
