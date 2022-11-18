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
from reframe.core.backends import getlauncher

# rfmdocstart: osupingpong
@rfm.simple_test
class StreamSingleVMTest(rfm.RunOnlyRegressionTest):
    descr = 'Stream Memory Benchmark on Single VMs'

    valid_systems = ['*']
    valid_prog_environs = ['*']

    @run_after('init')
    def set_stream_prerun_options(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        vmtype = vm_series.split("_",1)[0]
        source_path = self.prefix.split("reframe",1)[0]+'reframe'+'/azure_nhc/memory/stream-utils'
        self.prerun_cmds = [
            f"export SYSTEM={vmtype}",
            f"source {source_path}/setenv_AOCC.sh",
            ]
        if vm_series == 'hbrs_v3':
            self.prerun_cmds.append('export OMP_NUM_THREADS=16')
            self.prerun_cmds.append('export GOMP_CPU_AFFINITY="0,8,16,24,30,38,46,54,60,68,76,84,90,98,106,114"')
        if vm_series == 'hbrs_v2':
            self.prerun_cmds.append('export OMP_NUM_THREADS=32')
            self.prerun_cmds.append('export GOMP_CPU_AFFINITY="0,3,6,10,14,18,22,26,30,33,36,40,44,48,52,56,60,63,66,70,74,78,82,86,90,93,96,100,104,108,112,116"')

        self.executable = f"./stream-{vmtype} > stream-$(hostname).log"

    @run_before('run')
    def copy_files(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        vmtype = vm_series.split("_",1)[0]
        source_path = self.prefix.split("reframe",1)[0]+'reframe'+'/azure_nhc/memory/stream-utils'
        stage_path = self.stagedir 
        os.system(f"cp {source_path}/stream-{vmtype} {stage_path}/") 
        os.system(f"chmod +x {stage_path}/stream-{vmtype}")
        self.prerun_cmds.append(f"cd {self.stagedir}")

    cmda = "echo \" "
    cmdb = "system: $HOSTNAME stream: $(grep 'Triad:' ./stream*.log | awk -F ' ' '{print $2}')\""
    cmdc = "  > stream-test-results.log"
    cmd = cmda+cmdb+cmdc
    postrun_cmds = [
        'cat stream*.log',
        cmd,
    ]

    @run_before('run')
    def set_test_flags(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series'] 
        self.job.options = [
                '--nodes=1',
                '--ntasks=1',
                '--threads-per-core=1',
                '--exclusive'
        ]
        if vm_series == 'hbrs_v3':
            self.job.options.append('--cpus-per-task=120')
        if vm_series == 'hbrs_v2':
            self.job.options.append('--cpus-per-task=120')
        
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @sanity_function
    def assert_num_messages(self):
        num_tests = sn.len(sn.findall(r'stream: (\S+)',
                                         self.stagedir+'/stream-test-results.log'))
        return sn.assert_eq(num_tests, 1)

    @performance_function('MB/s')
    def extract_stream_s(self, vm='c5e'):
         return sn.extractsingle(rf'system: {vm} stream: (\S+)',self.stagedir+'/stream-test-results.log', 1, float)

    @run_before('performance')
    def set_perf_variables(self):
        '''Build the dictionary with all the performance variables.'''

        self.perf_variables = {}
        with open(self.stagedir+'/stream-test-results.log',"r") as f:
            sys_names = f.read()

        systems = re.findall(r"system:\s(\S+)\s+.*",sys_names,re.M)
        stream = re.findall(r"stream: (\S+)",sys_names,re.M)

        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        temp = {vm_series: {}}

        if vm_info != None and 'nhc_values' in vm_info:
            for i in systems:
                temp[vm_series][i] = (vm_info['nhc_values']['stream_triad'],
                                        vm_info['nhc_values']['stream_triad_limits'][0],
                                        vm_info['nhc_values']['stream_triad_limits'][1],
                                        'MB/s')

        self.reference = temp

        for i in systems:
            self.perf_variables[i] = self.extract_stream_s(i)

        results = {}
        for i in range(len(systems)):
            results[systems[i]] = stream[i]

        with open(self.outputdir+"/stream_test_results.json", "w") as outfile:
            js.dump(results, outfile, indent=4)

