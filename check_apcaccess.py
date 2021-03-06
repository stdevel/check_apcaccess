#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_apcaccess.py - a script for checking a APC UPS
using the apcaccess utility
See also https://github.com/stdevel/check_apcaccess
"""

import argparse
import subprocess
import sys
import logging
import re

__version__ = "0.6.0"
# set logger
LOGGER = logging.getLogger("check_apcaccess")
# global variables
UPS_INFO = {}
STATE = 0


def check_value(val, desc, warn, crit, reverse=False):
    """
    Compares value to thresholds and sets return code

    :param val: value
    :type val: int
    :param desc: description
    :type desc: str
    :param warn: warning threshold
    :type warn: int
    :param crit: critical threshold
    :type crit: int
    :param reverse: whether to invert comparison
    :type reverse: bool
    """
    LOGGER.debug(
        "Comparing '%s' (%s) to warn/crit thresholds %s/%s (reverse: %s)",
        val, desc, warn, crit, reverse
    )
    snip = ""
    if not reverse:
        if val > crit:
            # critical
            snip = "{0} critical ({1})".format(desc, val)
            set_code(2)
        elif val > warn:
            # warning
            snip = "{0} warning ({1})".format(desc, val)
            set_code(1)
        else:
            snip = "{0} okay ({1})".format(desc, val)
    else:
        if val < crit:
            # critical
            snip = "{0} critical ({1})".format(desc, val)
            set_code(2)
        elif val < warn:
            # warning
            snip = "{0} warning ({1})".format(desc, val)
            set_code(1)
        else:
            snip = "{0} okay ({1})".format(desc, val)

    return snip


def set_code(val):
    """
    sets result code

    :param val: return code
    :type val: int
    """
    global STATE
    if val > STATE:
        STATE = val


def get_return_str():
    """
    Returns return string
    """
    if STATE == 3:
        _state = "UNKNOWN"
    elif STATE == 2:
        _state = "CRITICAL"
    elif STATE == 1:
        _state = "WARNING"
    else:
        _state = "OK"
    return _state


def get_value(key, is_float=False):
    """
    Gets value from apcaccess information
    """
    if is_float:
        temp = re.findall(r"\d+", UPS_INFO[key])
        _return = float(temp[0])
    else:
        _return = UPS_INFO[key]
    return _return


def calc_consumption():
    """
    Calculates power consumption
    """
    load = get_value("LOADPCT", True)
    out = get_value("NOMOUTV", True)
    power_cons = load / 100 * out
    LOGGER.debug(
        "I assume that the power consumption might be ~%s watts",
        power_cons
    )
    return power_cons


def check_ups(options):
    """
    Checks UPS state
    """
    # get _all_ the values
    temp = get_value("ITEMP", True)
    load = get_value("LOADPCT", True)
    batt = get_value("BCHARGE", True)
    if options.time_warn and options.time_crit:
        time = get_value("TIMELEFT", True)
    power_cons = calc_consumption()

    # check temp
    snip_temp = check_value(
        temp, "temperature", options.temp_warn, options.temp_crit
    )

    # check load
    snip_load = check_value(
        load, "load", options.load_warn, options.temp_crit
    )

    # check battery load
    snip_batt = check_value(
        batt, "battery load",
        options.bat_warn,
        options.bat_crit,
        True
    )

    # check battery time (optional)
    if options.time_warn or options.time_crit:
        snip_time = check_value(
            time,
            "battery time",
            options.time_warn,
            options.time_crit,
            True
        )
    else:
        snip_time = ""

    # check power consumption (optional)
    if options.consum_warn or options.consum_crit:
        snip_consum = check_value(
            power_cons,
            "power consumption",
            options.consum_warn,
            options.consum_crit
        )
    else:
        snip_consum = ""

    # get performance data
    if options.show_perfdata:
        # initialize perfdata
        perfdata = " |"

        # power consumption
        if options.consum_warn and options.consum_crit:
            perfdata = "{0} 'consumption'={1};{2};{3};;".format(
                perfdata,
                power_cons,
                float(options.consum_warn),
                float(options.consum_crit),
            )
        else:
            perfdata = "{0} 'consumption'={1}".format(perfdata, power_cons)

        # temperature
        perfdata = "{0} 'temperature'={1};{2};{3};{4};{5}".format(
            perfdata,
            temp,
            float(options.temp_warn),
            float(options.temp_crit),
            0.0,
            100.0,
        )

        # load
        perfdata = "{0} 'load'={1};{2};{3};{4};{5}".format(
            perfdata,
            load,
            float(options.load_warn),
            float(options.load_crit),
            0.0,
            100.0,
        )

        # battery charge
        perfdata = "{0} 'battery_load'={1};{2};{3};{4};{5}".format(
            perfdata,
            batt,
            float(options.bat_warn),
            float(options.bat_crit),
            0.0,
            100.0
        )

        # battery time
        if options.time_warn or options.time_crit:
            perfdata = "{0} 'battery_time'={1};{2};{3};;".format(
                perfdata,
                time,
                float(options.time_warn),
                float(options.time_crit)
            )
    else:
        perfdata = ""

    # return result
    _filter = [snip_temp, snip_load, snip_batt, snip_time, snip_consum]
    snips = [x for x in _filter if x != ""]
    print(
        "{0}: {1}{2}".format(
            get_return_str(),
            str(", ".join(snips)),
            perfdata
        )
    )
    sys.exit(STATE)


def run_cmd(cmd=""):
    """
    Run a command, it's tricky!
    """
    output = subprocess.Popen(
        "LANG=C {0}".format(cmd), shell=True, stdout=subprocess.PIPE
    ).stdout.read()
    LOGGER.debug("Output of '%s => '%s", cmd, output)
    return output


def get_apcaccess_data(options):
    """
    Gets the output of apcaccess
    """
    global UPS_INFO

    raw_data = run_cmd("apcaccess -f {0}".format(options.file))
    raw_data = raw_data.splitlines()
    for line in raw_data:
        # parse lines to key/value dict
        key = line[: line.find(":")].strip()
        value = line[line.find(":") + 1:].strip()
        LOGGER.debug("Found key '%s' with value '%s'", key, value)
        UPS_INFO[key] = value


def parse_options():
    """Parses options and arguments."""
    desc = "%(prog)s is used to check a APC UPS using the apcaccess utility."
    epilog = "See also: https://github.com/stdevel/check_apcaccess"
    parser = argparse.ArgumentParser(description=desc, epilog=epilog)
    parser.add_argument('--version', action='version', version=__version__)

    gen_opts = parser.add_argument_group("Generic options")
    mon_opts = parser.add_argument_group("Monitoring options")
    thres_opts = parser.add_argument_group("Threshold options")

    # -d / --debug
    gen_opts.add_argument(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="enable debugging outputs",
    )

    # -f / --file
    gen_opts.add_argument(
        "-f",
        "--file",
        dest="file",
        default="/etc/apcupsd/apcupsd.conf",
        help="apcupsd configuration file (default: /etc/apcupsd/apcupsd.conf)",
    )

    # -P / --enable-perfdata
    mon_opts.add_argument(
        "-P",
        "--enable-perfdata",
        dest="show_perfdata",
        default=False,
        action="store_true",
        help="enables performance data (default: no)",
    )

    # -w / --temp-warning
    thres_opts.add_argument(
        "-w",
        "--temp-warning",
        dest="temp_warn",
        default=50,
        type=int,
        metavar="TEMP",
        action="store",
        help="defines temperature warning threshold (celsius, default: 50)",
    )

    # -c / --temp-critical
    thres_opts.add_argument(
        "-c",
        "--temp-critical",
        dest="temp_crit",
        default=60,
        type=int,
        metavar="TEMP",
        action="store",
        help="temperature critical threshold (celsius, default: 60)",
    )

    # -l / --load-warning
    thres_opts.add_argument(
        "-l",
        "--load-warning",
        dest="load_warn",
        default=50,
        type=int,
        metavar="PERCENT",
        action="store",
        help="load warning threshold (percent, default: 50)",
    )

    # -L / --load-critical
    thres_opts.add_argument(
        "-L",
        "--load-critical",
        dest="load_crit",
        default=80,
        type=int,
        metavar="PERCENT",
        action="store",
        help="load critical threshold (percent, default: 80)",
    )

    # -b / --battery-warning
    thres_opts.add_argument(
        "-b",
        "--battery-warning",
        dest="bat_warn",
        default=80,
        type=int,
        metavar="PERCENT",
        action="store",
        help="battery load warning threshold (percent, default: 80)",
    )

    # -B / --battery-critical
    thres_opts.add_argument(
        "-B",
        "--battery-critical",
        dest="bat_crit",
        default=50,
        type=int,
        metavar="PERCENT",
        action="store",
        help="battery load critical threshold (percent, default: 50)",
    )

    # -t / --time-warning
    thres_opts.add_argument(
        "-t",
        "--time-warning",
        dest="time_warn",
        type=int,
        metavar="TIME",
        action="store",
        help="battery time left warning threshold (minutes, default: empty)",
    )

    # -T / --time-critical
    thres_opts.add_argument(
        "-T",
        "--time-critical",
        dest="time_crit",
        type=int,
        metavar="TIME",
        action="store",
        help="battery time left critical threshold (minutes, default: empty)",
    )

    # -u / --consumption-warning
    thres_opts.add_argument(
        "-u",
        "--consumption-warning",
        dest="consum_warn",
        type=int,
        metavar="WATTS",
        action="store",
        help="power consumption warning threshold (watts, default: empty)",
    )

    # -U / --consumption-critical
    thres_opts.add_argument(
        "-U",
        "--consumption-critical",
        dest="consum_crit",
        type=int,
        metavar="WATTS",
        action="store",
        help="power consumption critical threshold (watts, default: empty)",
    )

    # parse arguments
    return parser.parse_args()


def cli():
    """
    This functions initializes the CLI interface
    """
    options = parse_options()

    # set logger level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)
    else:
        logging.basicConfig()
        LOGGER.setLevel(logging.INFO)

    # debug outputs
    LOGGER.debug("options: %s", options)

    # get information and check UPS state
    get_apcaccess_data(options)
    check_ups(options)


if __name__ == "__main__":
    cli()
