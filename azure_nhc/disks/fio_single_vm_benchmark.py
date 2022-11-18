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
class FioSingleVMTest(rfm.RunOnlyRegressionTest):
    descr = 'Quick FIO Storage Benchmark on Single VMs'
    disk_type = parameter(['ssd', 'nvme'])

    valid_systems = ['*']
    valid_prog_environs = ['*']

    @run_after('init')
    def set_fio_prerun_options(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        self.prerun_cmds.append('sudo yum install fio -y')
        if self.disk_type == 'ssd':
            cmd = "TEMP_DIR=$(mount | grep sdb1 | awk '{print $3}')/fiotest"
            self.prerun_cmds.append(cmd)
        elif self.disk_type == 'nvme':
            cmd = "if [[ ! -d /mnt/resource_nvme && -e /dev/nvme0n1 ]]; then sudo mkfs.ext4 /dev/nvme0n1; sudo mkdir -p /mnt/resource_nvme; sudo mount /dev/nvme0n1 /mnt/resource_nvme; sudo chmod 775 /dev/nvme0n1; sudo chmod 777 /mnt/resource_nvme/; fi"
            self.prerun_cmds.append(cmd)
            cmd = "TEMP_DIR=$(mount | grep nvme | awk '{print $3}')/fiotest"
            self.prerun_cmds.append(cmd)

        self.prerun_cmds.append("sudo mkdir -p $TEMP_DIR")
        self.prerun_cmds.append("sudo chmod 777 $TEMP_DIR")


    executable = 'fio'
    
    cmda = "echo \" system: $HOSTNAME FIOWriteTPT: "
    cmdb = "$(grep \"WRITE:\" fio*.log | awk '{print $2}' | cut -d '=' -f2 | cut -d 'M' -f1)\""
    cmdc = " > fio-test-results.log"
    cmd = cmda+cmdb+cmdc
    postrun_cmds = [
        'cat fio*.log',
         cmd,
        'rm $TEMP_DIR/*',
    ]

    @run_before('run')
    def set_fio_exec_options(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        disk_type = self.disk_type
        self.executable_opts = [
             '--name=write_throughput',
             '--directory=$TEMP_DIR',
             '--numjobs=4',
             '--size=2G',
             '--time_based',
             '--runtime=60s',
             '--ramp_time=2s',
             '--ioengine=libaio',
             '--direct=1',
             '--verify=0',
             '--bs=4M',
             '--iodepth=128',
             '--rw=write',
             '--group_reporting=1',
             f' > fio-$(hostname  | tr "[:upper:]" "[:lower:]")-{disk_type}.log'
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
        if vm_series == 'hbrs':
            self.job.options.append('--cpus-per-task=60')
        
    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @sanity_function
    def assert_num_messages(self):
        num_tests = sn.len(sn.findall(r'FIOWriteTPT: (\S+)',
                                         self.stagedir+'/fio-test-results.log'))
        return sn.assert_eq(num_tests, 1)

    @performance_function('MiB/s')
    def extract_fio_s(self, vm='c5e'):
         return sn.extractsingle(rf'system: {vm} FIOWriteTPT: (\S+)',self.stagedir+'/fio-test-results.log', 1, float)

    @run_before('performance')
    def set_perf_variables(self):
        '''Build the dictionary with all the performance variables.'''

        self.perf_variables = {}
        with open(self.stagedir+'/fio-test-results.log',"r") as f:
            sys_names = f.read()

        systems = re.findall(r"system:\s(\S+)\s+.*",sys_names,re.M)
        fio = re.findall(r"FIOWriteTPT: (\S+)",sys_names,re.M)

        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        temp = {vm_series: {}}

        if vm_info != None and 'nhc_values' in vm_info:
            for i in systems:
                temp[vm_series][i] = (vm_info['nhc_values']['fio_writetpt'],
                                        vm_info['nhc_values']['fio_writetpt_limits'][0],
                                        vm_info['nhc_values']['fio_writetpt_limits'][1],
                                        'MiB/s')

        self.reference = temp

        for i in systems:
            self.perf_variables[i] = self.extract_fio_s(i)

        results = {}
        for i in range(len(systems)):
            results[systems[i]] = fio[i]

        with open(self.outputdir+"/fio_test_results.json", "w") as outfile:
            js.dump(results, outfile, indent=4)

