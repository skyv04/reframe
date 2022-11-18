# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

# rfmdocstart: streamtest3
import os
import reframe as rfm
import reframe.utility.sanity as sn


# rfmdocstart: gpu_bw
@rfm.simple_test
class CudaBandwidthTest(rfm.RunOnlyRegressionTest):
    '''Base class for Cuda bandwidth benchmark runtime test'''
    #valid_systems = ['*']
    valid_prog_environs = ['*']
    valid_systems = ['ndasr_v4', 'ndamsr_a100_v4', 'ncads_a100_v4', 'ndrs_v2']
    executable = 'python3 check-vm-gpu-bw.py'
    #valid_prog_environs = ['gnu']

    @run_before('run')
    def prepare_run(self):
        vm_info = self.current_system.node_data
        vm_series = vm_info['vm_series']
        #print(vm_info)
        vmtype = vm_series.split("_",1)[0]
        source_path = self.prefix.split("reframe",1)[0]+'reframe'+'/azure_nhc/gpus/utils'
        #self.sourcesdir = source_path
        stage_path = self.stagedir 
        os.system(f"ln -s {source_path}/check-vm-gpu-bw.py {stage_path}/")
        os.system(f"ln -s {source_path}/gpu-bwtest {stage_path}/")

    @sanity_function
    def bandwidth_check(self):
        vm_info = self.current_system.node_data
        regex = r'(?P<device_id>\S+) : (?P<dtoh>\S+) : (?P<htod>\S+)'
        device_id = sn.extractall( regex, self.stdout, "device_id", str)
        dtoh = sn.extractall( regex, self.stdout, "dtoh", float)
        htod = sn.extractall( regex, self.stdout, "htod", float)
        print("Device id: {}".format(device_id))
        print("dtoh: {}".format(dtoh))
        print("htod: {}".format(htod))
        return sn.all([
            sn.assert_eq(sn.count(device_id), vm_info['nhc_values']['gpu_count']),
            sn.all(sn.map(lambda x: sn.assert_bounded(x, vm_info['nhc_values']['gpu_dtoh_bw_limits'][0], vm_info['nhc_values']['gpu_dtoh_bw_limits'][1]), dtoh)),
            sn.all(sn.map(lambda x: sn.assert_bounded(x, vm_info['nhc_values']['gpu_htod_bw_limits'][0], vm_info['nhc_values']['gpu_htod_bw_limits'][1]), htod))
        ])



# rfmdocend: gpu_bw.py 
