#!/usr/bin/env python
# -*- coding: utf-8 -*-

# check_apcaccess.py - a script for checking a APC UPS
# using the apcaccess utility
#
# 2016 By Christian Stankowic
# <info at stankowic hyphen development dot net>
# https://github.com/stdevel
#

from optparse import OptionParser, OptionGroup
import os
import subprocess
import logging
import re

#set logger
LOGGER = logging.getLogger("check_apcaccess")

#global variables
ups_info={}
state=0



def check_value(val, desc, warn, crit, reverse=False):
	#compares value to thresholds and sets codes
	LOGGER.debug("Comparing '{0}' ({1}) to warning/critical thresholds {2}/{3} (reverse: {4})".format(val, desc, warn, crit, reverse))
	snip=""
	if reverse == False:
		if val > crit:
			#critical
			snip="{0} critical ({1})".format(desc, val)
			set_code(2)
		elif val > warn:
			#warning
			snip="{0} warning ({1})".format(desc, val)
			set_code(1)
		else: snip="{0} okay ({1})".format(desc, val)
	else:
		if val < crit:
			#critical
			snip="{0} critical ({1})".format(desc, val)
			set_code(2)
		elif val < warn:
			#warning
			snip="{0} warning ({1})".format(desc, val)
			set_code(1)
		else: snip="{0} okay ({1})".format(desc, val)
		
	return snip



def set_code(int):
	#set result code
	global state
	if int > state: state = int



def get_return_str():
	#get return string
	if state == 3: return "UNKNOWN"
	elif state == 2: return "CRITICAL"
	elif state == 1: return "WARNING"
	else: return "OK"



def get_value(key, isFloat=False):
	#get value from apcaccess information
	if isFloat:
		temp = re.findall(r'\d+', ups_info[key])
		return float(temp[0])
	else: return ups_info[key]



def calc_consumption():
	#calculate power consumption
	load = get_value('LOADPCT', True)
	out = get_value('NOMOUTV', True)
	power_cons = load/100*out
	LOGGER.debug("I assume that the power consumption might be ~{0} watts".format(power_cons))
	return power_cons



def check_ups():
	#check UPS
	global state
	
	#get _all_ the values
	temp = get_value('ITEMP', True)
	load = get_value('LOADPCT', True)
	batt = get_value('BCHARGE', True)
	if options.time_warn and options.time_crit: time = get_value('TIMELEFT', True)
	power_cons = calc_consumption()
	
	#check temp
	snip_temp = check_value(temp, "temperature", options.temp_warn, options.temp_crit)
	
	#check load
	snip_load = check_value(load, "load", options.load_warn, options.load_crit)
	
	#check battery load
	snip_batt = check_value(batt, "battery load", options.bat_warn, options.bat_crit, True)
	
	#check battery time (optional)
	if options.time_warn or options.time_crit:
		snip_time = check_value(time, "battery time", options.time_warn, options.time_crit, True)
	else: snip_time=""
	
	#check power consumption (optional)
	if options.consum_warn or options.consum_crit:
		snip_consum = check_value(power_cons, "power consumption", options.consum_warn, options.consum_crit)
	else: snip_consum=""
	
	#get performance data
	if options.show_perfdata:
		#initialize perfdata
		perfdata=" |"
		
		#power consumption
		if options.consum_warn and options.consum_crit: perfdata = "{0} 'consumption'={1};{2};{3};;".format(perfdata, power_cons, float(options.consum_warn), float(options.consum_crit))
		else: perfdata = "{0} 'consumption'={1}".format(perfdata, power_cons)
		
		#temperature
		perfdata = "{0} 'temperature'={1};{2};{3};{4};{5}".format(perfdata, temp, float(options.temp_warn), float(options.temp_crit), 0.0, 100.0)
		
		#load
		perfdata = "{0} 'load'={1};{2};{3};{4};{5}".format(perfdata, load, float(options.load_warn), float(options.load_crit), 0.0, 100.0)
		
		#battery charge
		perfdata = "{0} 'battery_load'={1};{2};{3};{4};{5}".format(perfdata, batt, float(options.bat_warn), float(options.bat_crit), 0.0, 100.0)
		
		#battery time
		if options.time_warn or options.time_crit:
			perfdata =  "{0} 'battery_time'={1};{2};{3};;".format(perfdata, time, float(options.time_warn), float(options.time_crit))
	else: perfdata=""
	
	#return result
	snips = [x for x in [snip_temp, snip_load, snip_batt, snip_time, snip_consum] if x != ""]
	print "{0}: {1}{2}".format(get_return_str(), str(", ".join(snips)), perfdata)
	exit(state)



def run_cmd(cmd=""):
	#run the command, it's tricky!
	output = subprocess.Popen("LANG=C {0}".format(cmd), shell=True, stdout=subprocess.PIPE).stdout.read()
	LOGGER.debug("Output of '{0}' => '{1}".format(cmd, output))
	return output



def get_apcaccess_data():
	#get output of apcaccess
	global ups_info
	
	raw_data = run_cmd("apcaccess -f {0}".format(options.file))
	raw_data = raw_data.splitlines()
	for line in raw_data:
		#parse lines to key/value dict
		key=line[:line.find(":")].strip()
		value=line[line.find(":")+1:].strip()
		LOGGER.debug("Found key '{0}' with value '{1}'".format(key, value))
		ups_info[key]=value



if __name__ == "__main__":
	#define description, version and load parser
	desc='''%prog is used to check a APC UPS using the apcaccess utility.
	
	Checkout the GitHub page for updates: https://github.com/stdevel/check_apcaccess'''
	parser = OptionParser(description=desc,version="%prog version 0.5.1")
	
	gen_opts = OptionGroup(parser, "Generic options")
	mon_opts = OptionGroup(parser, "Monitoring options")
	thres_opts = OptionGroup(parser, "Threshold options")
	parser.add_option_group(gen_opts)
	parser.add_option_group(mon_opts)
	parser.add_option_group(thres_opts)
	
	#-d / --debug
	gen_opts.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help="enable debugging outputs")

        #-f / --file
        gen_opts.add_option("-f", "--file", dest="file", default="/etc/apcupsd/apcupsd.conf", help="defines the apcupsd configuration file (default: /etc/apcupsd/apcupsd.conf)")
	
	#-P / --enable-perfdata
	mon_opts.add_option("-P", "--enable-perfdata", dest="show_perfdata", default=False, action="store_true", help="enables performance data (default: no)")
	
	#-w / --temp-warning
	thres_opts.add_option("-w", "--temp-warning", dest="temp_warn", default=50, type=int, metavar="TEMP", action="store", help="defines temperature warning threshold in Celsius (default: 50 C)")
	
	#-c / --temp-critical
	thres_opts.add_option("-c", "--temp-critical", dest="temp_crit", default=60, type=int, metavar="TEMP", action="store", help="defines temperature critical threshold in Celsius (default: 60 C)")
	
	#-l / --load-warning
	thres_opts.add_option("-l", "--load-warning", dest="load_warn", default=50, type=int, metavar="PERCENT", action="store", help="defines load warning threshold in percent (default: 50%)")
	
	#-L / --load-critical
	thres_opts.add_option("-L", "--load-critical", dest="load_crit", default=80, type=int, metavar="PERCENT", action="store", help="defines load critical threshold in percent (default: 80%)")
	
	#-b / --battery-warning
	thres_opts.add_option("-b", "--battery-warning", dest="bat_warn", default=80, type=int, metavar="PERCENT", action="store", help="defines battery load warning threshold in percent (default: 80%)")
	
	#-B / --battery-critical
	thres_opts.add_option("-B", "--battery-critical", dest="bat_crit", default=50, type=int, metavar="PERCENT", action="store", help="defines battery load critical threshold in percent (default: 50%)")
	
	#-t / --time-warning
	thres_opts.add_option("-t", "--time-warning", dest="time_warn", type=int, metavar="TIME", action="store", help="defines battery time left warning threshold in minutes (default: empty)")
	
	#-T / --time-critical
	thres_opts.add_option("-T", "--time-critical", dest="time_crit", type=int, metavar="TIME", action="store", help="defines battery time left critical threshold in minutes (default: empty)")
	
	#-u / --consumption-warning
	thres_opts.add_option("-u", "--consumption-warning", dest="consum_warn", type=int, metavar="WATTS", action="store", help="defines power consumption warning threshold in watts (default: empty)")
	
	#-U / --consumption-critical
	thres_opts.add_option("-U", "--consumption-critical", dest="consum_crit", type=int, metavar="WATTS", action="store", help="defines power consumption critical threshold in watts (default: empty)")
	
	#parse arguments
	(options, args) = parser.parse_args()
	
	#set logger level
	if options.debug:
		logging.basicConfig(level=logging.DEBUG)
		LOGGER.setLevel(logging.DEBUG)
	else:
		logging.basicConfig()
		LOGGER.setLevel(logging.INFO)
	
	#debug outputs
	LOGGER.debug("OPTIONS: {0}".format(options))
	
	#get information
	get_apcaccess_data()
	
	#check UPS
	check_ups()
