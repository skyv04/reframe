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

@rfm.simple_test
class HPLSingleVMTest(rfm.RunOnlyRegressionTest):
    descr = 'HPL Single VM test using pssh'
    valid_systems = ['*']
    valid_prog_environs = ['*']
    
    @run_after('init')
    def def_ntasks(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        if vm_series == 'hbrs_v3':
            self.num_tasks = 16
        elif vm_series == 'hbrs_v2':
            self.num_tasks = 32
        elif vm_series == 'hbrs':
            self.num_tasks = 15
        elif vm_series == 'hcrs':
            self.num_tasks = 4

    @run_before('run')
    def copy_files(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        vmtype = vm_series.split("_",1)[0]
        source_path = self.prefix.split("reframe",1)[0]+'reframe'+'/azure_nhc/system/hpl-utils'
        #self.sourcesdir = source_path
        stage_path = self.stagedir 
        os.system(f"cp -r {source_path}/xhpl-{vmtype} {stage_path}/") 
        os.system(f"cp -r {source_path}/appfile_ccx_{vm_series} {stage_path}/")
        os.system(f"cp -r {source_path}/xhpl_ccx.sh {stage_path}/")
        os.system(f"cp -r {source_path}/HPL.dat {stage_path}/")
        os.system(f"chmod +x {stage_path}/xhpl-{vmtype}")
        os.system(f"chmod +x {stage_path}/appfile_ccx_{vm_series}")
        os.system(f"chmod +x {stage_path}/xhpl_ccx.sh")
  
    @run_after('init')
    def set_hpl_prerun_options(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        vmtype = vm_series.split("_",1)[0]
        self.prerun_cmds = [
            f"export SYSTEM={vmtype}",
            'echo $(hostname)',
            'echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled',
            'echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag',
            ]
        if vm_series == 'hbrs_v2':
            self.prerun_cmds.append('sed -i "s/4           Ps/6           Ps/g" HPL.dat')
            self.prerun_cmds.append('sed -i "s/4            Qs/5            Qs/g" HPL.dat')
        if vm_series == 'hbrs':
            self.prerun_cmds.append('sed -i "s/4           Ps/5           Ps/g" HPL.dat')
            self.prerun_cmds.append('sed -i "s/4            Qs/3            Qs/g" HPL.dat')
        if vm_series == 'hcrs':
            self.prerun_cmds.append('sed -i "s/4           Ps/2           Ps/g" HPL.dat')
            self.prerun_cmds.append('sed -i "s/4            Qs/2            Qs/g" HPL.dat')

    executable = 'mpirun'
    cmda = "echo "
    cmdb = "system: $HOSTNAME HPL: $(grep WR hpl*.log | awk -F ' ' '{print $7}')"
    cmdc = "  >> hpl-test-results.log"
    cmd = cmda+cmdb+cmdc
    postrun_cmds = [
        'cat hpl*.log',
        cmd,
    ]

    @run_before('run')
    def set_hpl_options(self):
        self.prerun_cmds.append(f"cd {self.stagedir}")
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        if vm_series == 'hbrs_v3':
            self.executable_opts = [
                '-np 16',
                '--mca mpi_leave_pinned 1',
                '--bind-to none',
                '--report-bindings',
                '--mca btl self,vader',
                '--map-by ppr:1:l3cache',
                '-x OMP_NUM_THREADS=6',
                '-x OMP_PROC_BIND=TRUE',
                '-x OMP_PLACES=cores',
                '-x LD_LIBRARY_PATH',
                '-app ./appfile_ccx_hbrs_v3  >> hpl-$HOSTNAME.log'
            ]
            self.job.options = [
                '--nodes=1',
                '--ntasks=16',
                '--cpus-per-task=6',
                '--threads-per-core=1'
            ]
        elif vm_series == 'hbrs_v2':
            self.executable_opts = [
                '-np 32',
                '--mca mpi_leave_pinned 1',
                '--bind-to none',
                '--report-bindings',
                '--mca btl self,vader',
                '--map-by ppr:1:l3cache',
                '-x OMP_NUM_THREADS=3',
                '-x OMP_PROC_BIND=TRUE',
                '-x OMP_PLACES=cores',
                '-x LD_LIBRARY_PATH',
                '-app ./appfile_ccx_hbrs_v2  >> hpl-$HOSTNAME.log'
            ]
            self.job.options = [
                '--nodes=1',
                '--ntasks=32',
                '--cpus-per-task=3',
                '--threads-per-core=1'
            ]
        elif vm_series == 'hbrs':
            self.executable_opts = [
                '-np 15',
                '--mca mpi_leave_pinned 1',
                '--bind-to none',
                '--report-bindings',
                '--mca btl self,vader',
                '--map-by ppr:1:l3cache',
                '-x OMP_NUM_THREADS=4',
                '-x OMP_PROC_BIND=TRUE',
                '-x OMP_PLACES=cores',
                '-x LD_LIBRARY_PATH',
                '-app ./appfile_ccx_hbrs  >> hpl-$HOSTNAME.log'
            ]
            self.job.options = [
                '--nodes=1',
                '--ntasks=15',
                '--cpus-per-task=4',
                '--threads-per-core=1'
            ]
        elif vm_series == 'hcrs':
            self.executable_opts = [
                '-np 4',
                '--mca mpi_leave_pinned 1',
                '--bind-to none',
                '--report-bindings',
                '--mca btl self,vader',
                '--map-by ppr:1:l3cache',
                '-x OMP_NUM_THREADS=11',
                '-x OMP_PROC_BIND=TRUE',
                '-x OMP_PLACES=cores',
                '-x LD_LIBRARY_PATH',
                '-app ./appfile_ccx_hcrs  >> hpl-$HOSTNAME.log'
            ]
            self.job.options = [
                '--nodes=1',
                '--ntasks=4',
                '--cpus-per-task=11',
                '--threads-per-core=1'
            ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('local')()

    @sanity_function
    def assert_num_messages(self):
        num_tests = sn.len(sn.findall(r'HPL: (\S+)',
                                         self.stagedir+'/hpl-test-results.log'))
        return sn.assert_eq(num_tests, 1)

    @performance_function('Gflops')
    def extract_hpl_s(self, vm='c5e'):
         return sn.extractsingle(rf'system: {vm} HPL: (\S+)',self.stagedir+'/hpl-test-results.log', 1, float)


    @run_before('performance')
    def set_perf_variables(self):
        
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


