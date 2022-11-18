#!/usr/bin/env python3
import json as js
import re
#####################################################################################
### Output File
js_output_file = "azure_vms_dataset.json"
### Input File: original azure dataset
js_filename = "azure_vm_info.json"
### Input File: original NHC dataset
js_filename2 = "azure_vm_info_addon.json"

#####################################################################################

js_file = open(js_filename)
vm_data = js.load(js_file)

tmp_data = {}
for vm in vm_data:
#    print(vm["name"])
    if "resourceType" in vm and vm["resourceType"] == "virtualMachines":
        if vm["name"] not in tmp_data:
            tmp_data[vm["name"]] = vm

vm_data = tmp_data

#define vm_series
for vm in vm_data.keys():
    tmp_data = re.split('([0-9]+(-[0-9]+)?)',vm_data[vm]['size'],1)
    if len(tmp_data) < 4:
        print("Tmp data not as expected: {}".format(tmp_data))
        continure

    vm_series = tmp_data[0] + tmp_data[-1]
    vm_data[vm]['series'] = vm_series.lower()

js_file2 = open(js_filename2)
vm_data2 = js.load(js_file2)

mod_vm = vm_data

#adding the nhc data for vm families to the file
for vm in vm_data.keys():
    for vmt in vm_data2["family"].keys():
        if vm_data[vm]["family"] == vmt:
            mod_vm[vm]['nhc_values'] = vm_data2["family"][vmt]

#adding the hardware specific data
for vm in mod_vm.keys():
    if 'nhc_values' in mod_vm[vm]:
        if mod_vm[vm]['nhc_values']["eth_type"] in vm_data2["hardware"].keys():
            mod_vm[vm]['nhc_values'].update(vm_data2["hardware"][mod_vm[vm]['nhc_values']["eth_type"]]) 
        if "ib_type" in mod_vm[vm]['nhc_values'].keys() and mod_vm[vm]['nhc_values']["ib_count"] > 0:
            mod_vm[vm]['nhc_values'].update(vm_data2["hardware"][mod_vm[vm]['nhc_values']["ib_type"]])
        if "gpu_type" in mod_vm[vm]['nhc_values'].keys() and mod_vm[vm]['nhc_values']["gpu_count"] > 0:
            mod_vm[vm]['nhc_values'].update(vm_data2["hardware"][mod_vm[vm]['nhc_values']["gpu_type"]])
        if "nvme_type" in mod_vm[vm]['nhc_values'].keys() and mod_vm[vm]['nhc_values']["nvme_count"] > 0:
            mod_vm[vm]['nhc_values'].update(vm_data2["hardware"][mod_vm[vm]['nhc_values']["nvme_type"]])

#convert cabilities section from list of dictionaries to a dictionary
for vm in mod_vm.keys():
    if 'capabilities' in mod_vm[vm]:
        new_dict = {}
        for item in mod_vm[vm]['capabilities']:
            new_dict[item['name']] = item['value']
        mod_vm[vm]['capabilities'] = new_dict

#adding the vm specific exceptions for the nhc data
for vm in mod_vm.keys():
    for vmt in vm_data2["vm_sizes"].keys():
        if vmt == vm:
            for en in vm_data2["vm_sizes"][vmt].keys():
                mod_vm[vmt]['nhc_values'][en] = vm_data2["vm_sizes"][vmt][en]


with open(js_output_file, "w") as outfile:
        js.dump(mod_vm, outfile, indent=4)

