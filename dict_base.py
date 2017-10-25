#!/usr/bin/env python3

#test_dict = {}
#test_dict['MODT-1.2.1'] = ['gps', 'ssh', '']
#test_dict['MODT-1.2.1'] = ['dut':'gps','connectivity' : 'ssh' ]

test_dict = {'MODT-1.2.1': {'dut':'gps', 'connectivity':'ssh'},
 'MODT-1.2.2':{'dut':'gps', 'connectivity':'ssh', 'nmag':True}}

for key, value in test_dict.items():
	print (key, value)

print (test_dict['MODT-1.2.1']['connectivity'])