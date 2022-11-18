# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

# rfmdocstart: streamtest4
import reframe as rfm
import reframe.utility.sanity as sn
import inspect
import reframe.core.config as cfg
import pprint

@rfm.simple_test
class IBCardCheck(rfm.RunOnlyRegressionTest):
    descr = 'Check the number of IB cards'
    valid_systems = ['*']
    valid_prog_environs = ['*']
    executable = 'ibstat'

    @sanity_function
    def validate_results(self):
        # Get node_data
        vm_info = self.current_system.node_data
        if 'runtime_data' not in self.current_system.node_data:
           self.current_system.node_data['runtime_data'] = {}
        self.current_system.node_data['runtime_data']['accelnet'] = True


        # Ideas for refactoring:
        # - get each name from ibstat -l and then check each one with ibstatus
        #   to see if the link_layer is InfiniBand or Ethernet (AccelNet)
        regex = r'CA\s+(?P<device_name>\S+)(.|\n)*?State:\s+(?P<device_state>\S+)(.|\n)*?Physical state:\s+(?P<device_pstate>\S+)(.|\n)*?Rate:\s+(?P<device_rate>\S+)(.|\n)*?Link layer:\s+(?P<device_type>\S+)'
        device_name = sn.extractall( regex, self.stdout, "device_name", str)
        device_state = sn.extractall( regex, self.stdout, "device_state", str)
        device_pstate = sn.extractall( regex, self.stdout, "device_pstate", str)
        device_rate = sn.extractall( regex, self.stdout, "device_rate", str)
        device_ll = sn.extractall( regex, self.stdout, "device_type", str)
        print("Device Names: {}".format(device_name))
        print("Device State: {}".format(device_state))
        print("Device Physical State: {}".format(device_pstate))
        print("Device Rate: {}".format(device_rate))
        print("Device Link Layer: {}".format(device_ll))

        # Loop through the devices found and verify that they properly report their values.
        ib_names = []
        ib_states = []
        ib_pstates = []
        ib_rates = []
        eth_names = []
        eth_states = []
        eth_pstates = []
        eth_rates = []


        for x,ll in enumerate(device_ll):
            print("Link Layer: {}, Device: {}, Rate: {}, State: {}, Physical State: {}".format(ll,device_name[x],device_rate[x],device_state[x],device_pstate[x]))
            # Separate devices based on link layer type
            if ll == "InfiniBand":
                ib_names.append(device_name[x])
                ib_rates.append(device_rate[x])
                ib_states.append(device_state[x])
                ib_pstates.append(device_pstate[x])
            elif ll == "Ethernet":
                eth_names.append(device_name[x])
                eth_rates.append(device_rate[x])
                eth_states.append(device_state[x])
                eth_pstates.append(device_pstate[x])
            else:
                print("Undefined Link Layer: {}".format(ll))
            
        print("IB Names: {}".format(ib_names))
        print("IB States: {}".format(ib_states))
        print("IB Rates: {}".format(ib_rates))
        print("IB Physical States: {}".format(ib_pstates))
        #return sn.assert_eq(sn.count(ib_count), 1 )
        #print("=====================")
        #pprint.pprint(vars(self.current_system))
        #print("=========------------============")
        if vm_info != None and 'nhc_values' in vm_info and "ib_count" in vm_info['nhc_values']:
            return sn.all([
                sn.assert_eq(sn.count(ib_names), vm_info['nhc_values']['ib_count']),
                sn.all(sn.map(lambda x: sn.assert_eq(x, vm_info['nhc_values']['ib_rate']),ib_rates)),
                sn.all(sn.map(lambda x: sn.assert_eq(x, vm_info['nhc_values']['ib_state']),ib_states)),
                sn.all(sn.map(lambda x: sn.assert_eq(x, vm_info['nhc_values']['ib_pstate']),ib_pstates))
            ])
        else:
            print("ib_count not found in vm_info['nhc_values']")
            return sn.assert_eq(sn.count(ib_names), 0)


