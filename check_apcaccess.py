#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_apcaccess.py - a script for checking a APC UPS
using the apcaccess utility.

2016 By Christian Stankowic
<info at stankowic hyphen development dot net>
https://github.com/stdevel
"""

from optparse import OptionParser, OptionGroup
import subprocess
import logging
import re
import sys

# set logger
LOGGER = logging.getLogger("check_apcaccess")

# global variables
UPS_INFO = {}
STATE = 0


def check_value(val, desc, warn, crit, reverse=False):
    """
    Compares value to thresholds and sets codes
    """
    LOGGER.debug(
        "Comparing '%s' (%s) to warning/critical thresholds %s/%s (reverse: %s)",
        val,
        desc,
        warn,
        crit,
        reverse,
    )
    snip = ""
    if reverse is False:
        if val > crit:
            # critical
            snip = f"{desc} critical ({val})"
            set_code(2)
        elif val > warn:
            # warning
            snip = f"{desc} warning ({val})"
            set_code(1)
        else:
            snip = f"{desc} okay ({val})"
    else:
        if val < crit:
            # critical
            snip = f"{desc} critical ({val})"
            set_code(2)
        elif val < warn:
            # warning
            snip = f"{desc} warning ({val})"
            set_code(1)
        else:
            snip = f"{desc} okay ({val})"

    return snip


def set_code(my_int):
    """
    Set result code
    """
    global STATE
    if my_int > STATE:
        STATE = my_int


def get_return_str():
    """
    Get return string
    """
    if STATE == 3:
        return "UNKNOWN"
    if STATE == 2:
        return "CRITICAL"
    if STATE == 1:
        return "WARNING"
    return "OK"


def get_value(key, is_float=False):
    """
    Get value from apcaccess information
    """
    try:
        if is_float:
            temp = re.findall(r"\d+", UPS_INFO[key])
            return float(temp[0])
        return UPS_INFO[key]
    except KeyError:
        return 0.0


def calc_consumption():
    """
    Calculate power consumption
    """
    load = get_value("LOADPCT", True)
    out = get_value("NOMOUTV", True)
    power_cons = load / 100 * out
    LOGGER.debug("I assume that the power consumption might be ~%s watts", power_cons)
    return power_cons


def check_ups(my_options):
    """
    Check UPS
    """
    # get _all_ the values
    temp = get_value("ITEMP", True)
    load = get_value("LOADPCT", True)
    batt = get_value("BCHARGE", True)
    if my_options.time_warn and my_options.time_crit:
        time = get_value("TIMELEFT", True)
    power_cons = calc_consumption()

    # check temp
    snip_temp = check_value(
        temp, "temperature", my_options.temp_warn, my_options.temp_crit
    )

    # check load
    snip_load = check_value(load, "load", my_options.load_warn, my_options.load_crit)

    # check battery load
    snip_batt = check_value(
        batt, "battery load", my_options.bat_warn, my_options.bat_crit, True
    )

    # check battery time (optional)
    if my_options.time_warn or my_options.time_crit:
        snip_time = check_value(
            time, "battery time", my_options.time_warn, my_options.time_crit, True
        )
    else:
        snip_time = ""

    # check power consumption (optional)
    if my_options.consum_warn or my_options.consum_crit:
        snip_consum = check_value(
            power_cons,
            "power consumption",
            my_options.consum_warn,
            my_options.consum_crit,
        )
    else:
        snip_consum = ""

    # get performance data
    if my_options.show_perfdata:
        # initialize perfdata
        perfdata = " |"

        # power consumption
        if my_options.consum_warn and my_options.consum_crit:
            perfdata = f"{perfdata} 'consumption'={power_cons};{float(my_options.consum_warn)};{float(my_options.consum_crit)};;"
        else:
            perfdata = f"{perfdata} 'consumption'={power_cons}"

        # temperature
        perfdata = f"{perfdata} 'temperature'={temp};{float(my_options.temp_warn)};{float(my_options.temp_crit)};{0.0};{100.0}"

        # load
        perfdata = f"{perfdata} 'load'={load};{float(my_options.load_warn)};{float(my_options.load_crit)};{0.0};{100.0}"

        # battery charge
        perfdata = f"{perfdata} 'battery_load'={batt};{float(my_options.bat_warn)};{float(my_options.bat_crit)};{0.0};{100.0}"

        # battery time
        if my_options.time_warn or my_options.time_crit:
            perfdata = f"{perfdata} 'battery_time'={time};{float(my_options.time_warn)};{float(my_options.time_crit)};;"
    else:
        perfdata = ""

    # return result
    snips = [
        x for x in [snip_temp, snip_load, snip_batt, snip_time, snip_consum] if x != ""
    ]
    status = str(", ".join(snips))
    print(f"{get_return_str()}: {status}{perfdata}")
    sys.exit(STATE)


def run_cmd(cmd=""):
    """
    Run the command, it's tricky!
    """
    with subprocess.Popen(f"LANG=C {cmd}", shell=True, stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read()

    LOGGER.debug("Output of '%s' => '%s", cmd, output)
    return output


def get_apcaccess_data(my_options):
    """
    Get output of apcaccess
    """
    global UPS_INFO

    raw_data = run_cmd(f"apcaccess -f {my_options.file}")
    raw_data = raw_data.splitlines()
    for line in raw_data:
        # parse lines to key/value dict
        key = line[:str(line).find(":")].strip()
        value = line[str(line).find(":") + 1 :].strip()
        LOGGER.debug("Found key '%s' with value '%s'", key, value)
        UPS_INFO[key] = value


if __name__ == "__main__":
    # Define description, version and load parser
    DESC = """%prog is used to check a APC UPS using the apcaccess utility.
    
    Checkout the GitHub page for updates: https://github.com/stdevel/check_apcaccess"""
    parser = OptionParser(description=DESC, version="%prog version 0.5.1")

    gen_opts = OptionGroup(parser, "Generic options")
    mon_opts = OptionGroup(parser, "Monitoring options")
    thres_opts = OptionGroup(parser, "Threshold options")
    parser.add_option_group(gen_opts)
    parser.add_option_group(mon_opts)
    parser.add_option_group(thres_opts)

    # -d / --debug
    gen_opts.add_option(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="enable debugging outputs",
    )

    # -f / --file
    gen_opts.add_option(
        "-f",
        "--file",
        dest="file",
        default="/etc/apcupsd/apcupsd.conf",
        help="defines the apcupsd configuration file (default: /etc/apcupsd/apcupsd.conf)",
    )

    # -P / --enable-perfdata
    mon_opts.add_option(
        "-P",
        "--enable-perfdata",
        dest="show_perfdata",
        default=False,
        action="store_true",
        help="enables performance data (default: no)",
    )

    # -w / --temp-warning
    thres_opts.add_option(
        "-w",
        "--temp-warning",
        dest="temp_warn",
        default=50,
        type=int,
        metavar="TEMP",
        action="store",
        help="defines temperature warning threshold in Celsius (default: 50 C)",
    )

    # -c / --temp-critical
    thres_opts.add_option(
        "-c",
        "--temp-critical",
        dest="temp_crit",
        default=60,
        type=int,
        metavar="TEMP",
        action="store",
        help="defines temperature critical threshold in Celsius (default: 60 C)",
    )

    # -l / --load-warning
    thres_opts.add_option(
        "-l",
        "--load-warning",
        dest="load_warn",
        default=50,
        type=int,
        metavar="PERCENT",
        action="store",
        help="defines load warning threshold in percent (default: 50%)",
    )

    # -L / --load-critical
    thres_opts.add_option(
        "-L",
        "--load-critical",
        dest="load_crit",
        default=80,
        type=int,
        metavar="PERCENT",
        action="store",
        help="defines load critical threshold in percent (default: 80%)",
    )

    # -b / --battery-warning
    thres_opts.add_option(
        "-b",
        "--battery-warning",
        dest="bat_warn",
        default=80,
        type=int,
        metavar="PERCENT",
        action="store",
        help="defines battery load warning threshold in percent (default: 80%)",
    )

    # -B / --battery-critical
    thres_opts.add_option(
        "-B",
        "--battery-critical",
        dest="bat_crit",
        default=50,
        type=int,
        metavar="PERCENT",
        action="store",
        help="defines battery load critical threshold in percent (default: 50%)",
    )

    # -t / --time-warning
    thres_opts.add_option(
        "-t",
        "--time-warning",
        dest="time_warn",
        type=int,
        metavar="TIME",
        action="store",
        help="defines battery time left warning threshold in minutes (default: empty)",
    )

    # -T / --time-critical
    thres_opts.add_option(
        "-T",
        "--time-critical",
        dest="time_crit",
        type=int,
        metavar="TIME",
        action="store",
        help="defines battery time left critical threshold in minutes (default: empty)",
    )

    # -u / --consumption-warning
    thres_opts.add_option(
        "-u",
        "--consumption-warning",
        dest="consum_warn",
        type=int,
        metavar="WATTS",
        action="store",
        help="defines power consumption warning threshold in watts (default: empty)",
    )

    # -U / --consumption-critical
    thres_opts.add_option(
        "-U",
        "--consumption-critical",
        dest="consum_crit",
        type=int,
        metavar="WATTS",
        action="store",
        help="defines power consumption critical threshold in watts (default: empty)",
    )

    # parse arguments
    (options, args) = parser.parse_args()

    # set logger level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)
    else:
        logging.basicConfig()
        LOGGER.setLevel(logging.INFO)

    # debug outputs
    LOGGER.debug("OPTIONS: %s", options)

    # get information
    get_apcaccess_data(options)

    # check UPS
    check_ups(options)
