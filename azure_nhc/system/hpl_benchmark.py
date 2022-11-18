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
class HPLBenchmarkTestBase(rfm.RunOnlyRegressionTest):
    '''Base class of HPL benchmark runtime tests'''

    valid_systems = ['*:default']
    valid_prog_environs = ['gnu-azhpc']
    sourcesdir = None

    # rfmdocstart: set_deps
    @run_after('init')
    def set_dependencies(self):
        self.depends_on('HPLBuildTest', udeps.by_env)
    # rfmdocend: set_deps

@rfm.simple_test
class HPLAllVMsTest(HPLBenchmarkTestBase):
    descr = 'HPL ALL VMs test using pssh'

    # rfmdocstart: set_exec
    @require_deps
    def set_sourcedir(self, HPLBuildTest):
        self.sourcesdir = os.path.join(
            HPLBuildTest(part='default', environ='gnu-azhpc').stagedir,
            ''
        )

    executable = './hpl_pssh_script.sh'
    postrun_cmds = [
        'list=($(ls -d HPL-N*)); for i in ${list[@]}; do cat $i/hpl*.log; done',
        'cat hpl-test-results.log',
    ]

    @run_before('run')
    def set_vm_series(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        self.variables = {
            'VM_SERIES': vm_series
        }

    @sanity_function
    def assert_num_messages(self):
        num_tests = sn.len(sn.findall(r'HPL: (\S+)',
                                         self.stagedir+'/hpl-test-results.log'))
        num_nodes = sum(1 for _ in open(self.stagedir+'/hosts.txt'))
        return sn.assert_eq(num_tests, num_nodes)

    @performance_function('Gflops')
    def extract_hpl_s(self, vm='c5e'):
         return sn.extractsingle(rf'system: {vm} HPL: (\S+)',self.stagedir+'/hpl-test-results.log', 1, float)

    @run_before('performance')
    def set_perf_variables(self):
        '''Build the dictionary with all the performance variables.'''

        self.perf_variables = {}
        with open(self.stagedir+'/hpl-test-results.log',"r") as f:
            sys_names = f.read()

        systems = re.findall(r"system:\s(\S+)\s+.*",sys_names,re.M)
        hpl = re.findall(r"HPL: (\S+)",sys_names,re.M)

        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        temp = {vm_series: {}}

        if vm_info != None and 'nhc_values' in vm_info:
            for i in systems:
                temp[vm_series][i] = (vm_info['nhc_values']['hpl_performance'],
                                        vm_info['nhc_values']['hpl_performance_limits'][0],
                                        vm_info['nhc_values']['hpl_performance_limits'][1],
                                        'Gflops')

        self.reference = temp

        for i in systems:
            self.perf_variables[i] = self.extract_hpl_s(i)

        results = {}
        for i in range(len(systems)):
            results[systems[i]] = hpl[i]

        with open(self.outputdir+"/hpl_test_results.json", "w") as outfile:
            js.dump(results, outfile, indent=4)


@rfm.simple_test
class HPLBuildTest(rfm.RunOnlyRegressionTest):
    descr = 'HPL benchmark build test'
    valid_systems = ['*:default']
    valid_prog_environs = ['gnu-azhpc']
    executable = './hpl_build_script.sh'

    @run_after('init')
    def inject_dependencies(self):
        self.depends_on('HPLDownloadTest', udeps.fully)

    @require_deps
    def set_sourcedir(self, HPLDownloadTest):
        self.sourcesdir = os.path.join(
            HPLDownloadTest(part='default', environ='gnu-azhpc').stagedir,
            ''
        )

    @sanity_function
    def validate_download(self):
        return sn.assert_true(os.path.exists('xhpl'))

# rfmdocstart: HPL download
@rfm.simple_test
class HPLDownloadTest(rfm.RunOnlyRegressionTest):
    descr = 'HPL benchmarks download sources'
    valid_systems = ['*:default']
    valid_prog_environs = ['gnu-azhpc']
    executable = 'wget'
    executable_opts = [
        'https://raw.githubusercontent.com/arstgr/hpl/main/hpl_build_script.sh'  
    ]
    postrun_cmds = [
        'chmod +x hpl_build_script.sh'
    ]

    @sanity_function
    def validate_download(self):
        return sn.assert_true(os.path.exists('hpl_build_script.sh'))
# rfmdocend: HPL download
