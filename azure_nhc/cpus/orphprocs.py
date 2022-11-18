# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import json as js
import re

import reframe as rfm
import reframe.utility.sanity as sn
import reframe.utility.udeps as udeps

# rfmdocstart: finding orphan processes
class OrphProcsTestBase(rfm.RunOnlyRegressionTest):
    '''Base class of OrphProcs runtime tests'''

    valid_systems = ['*:default']
    valid_prog_environs = ['gnu-azhpc']
    sourcesdir = None

    # rfmdocstart: set_deps
    @run_after('init')
    def set_dependencies(self):
        self.depends_on('OrphProcsDownloadTest', udeps.by_env)
    # rfmdocend: set_deps

@rfm.simple_test
class OrphProcsAllVMsTest(OrphProcsTestBase):
    descr = 'Identify Orphan Processes on ALL VMs using pssh'

    # rfmdocstart: set_exec
    @require_deps
    def set_sourcedir(self, OrphProcsDownloadTest):
        self.sourcesdir = os.path.join(
            OrphProcsDownloadTest(part='default', environ='gnu-azhpc').stagedir,
            ''
        )

    executable = './nhc_multi_node_orphprocs.py'
    executable_opts = [
       '--avg-load-threshold 10',
       '--inst-load-threshold 20'
       ]

    postrun_cmds = [
        'cat VM_loads.json',
        'cat VM_loads_summary.json',
        'sleep 1'
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
        num_tests = sn.len(sn.findall(r'STATUS',
                                         self.stagedir+'/VM_loads.json'))
        num_nodes = sum(1 for _ in open(self.stagedir+'/hosts.txt'))
        return sn.assert_eq(num_tests, num_nodes) and sn.assert_not_found(r'FAILED', self.stagedir+'/VM_loads_summary.json')

    @run_before('performance')
    def set_perf_variables(self):
        '''Build the dictionary with all the performance variables.'''

        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        summary = {vm_series: {}}

        results = {}
        with open(self.stagedir+"/VM_loads_summary.json") as js_file:
            results = js.load(js_file)
        summary[vm_series] = results

        json_output = js.dumps(summary, indent = 4)
        print("Test Summary: {}".format(json_output))

# rfmdocstart: nhc_multi_node_orphprocs.py download
@rfm.simple_test
class OrphProcsDownloadTest(rfm.RunOnlyRegressionTest):
    descr = 'OrphProcs test downloading sources'
    valid_systems = ['*:default']
    valid_prog_environs = ['gnu-azhpc']
    executable = 'wget'
    executable_opts = [
        'https://raw.githubusercontent.com/arstgr/orphprocs/main/nhc_multi_node_orphprocs.py'  # noqa: E501
    ]
    postrun_cmds = [
        'chmod +x nhc_multi_node_orphprocs.py'
    ]

    @sanity_function
    def validate_download(self):
        return sn.assert_true(os.path.exists('nhc_multi_node_orphprocs.py'))
# rfmdocend: nhc_multi_node_orphprocs.py download
