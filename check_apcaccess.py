#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_apcaccess.py - a script for checking a APC UPS
using the apcaccess utility
See also https://github.com/stdevel/check_apcaccess
"""

from optparse import OptionParser, OptionGroup
import subprocess
import sys
import logging
import re

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


def check_ups():
    """
    Checks UPS state
    """
    # get _all_ the values
    temp = get_value("ITEMP", True)
    load = get_value("LOADPCT", True)
    batt = get_value("BCHARGE", True)
    if OPTIONS.time_warn and OPTIONS.time_crit:
        time = get_value("TIMELEFT", True)
    power_cons = calc_consumption()

    # check temp
    snip_temp = check_value(
        temp, "temperature", OPTIONS.temp_warn, OPTIONS.temp_crit
    )

    # check load
    snip_load = check_value(
        load, "load", OPTIONS.load_warn, OPTIONS.temp_crit
    )

    # check battery load
    snip_batt = check_value(
        batt, "battery load",
        OPTIONS.bat_warn,
        OPTIONS.bat_crit,
        True
    )

    # check battery time (optional)
    if OPTIONS.time_warn or OPTIONS.time_crit:
        snip_time = check_value(
            time,
            "battery time",
            OPTIONS.time_warn,
            OPTIONS.time_crit,
            True
        )
    else:
        snip_time = ""

    # check power consumption (optional)
    if OPTIONS.consum_warn or OPTIONS.consum_crit:
        snip_consum = check_value(
            power_cons,
            "power consumption",
            OPTIONS.consum_warn,
            OPTIONS.consum_crit
        )
    else:
        snip_consum = ""

    # get performance data
    if OPTIONS.show_perfdata:
        # initialize perfdata
        perfdata = " |"

        # power consumption
        if OPTIONS.consum_warn and OPTIONS.consum_crit:
            perfdata = "{0} 'consumption'={1};{2};{3};;".format(
                perfdata,
                power_cons,
                float(OPTIONS.consum_warn),
                float(OPTIONS.consum_crit),
            )
        else:
            perfdata = "{0} 'consumption'={1}".format(perfdata, power_cons)

        # temperature
        perfdata = "{0} 'temperature'={1};{2};{3};{4};{5}".format(
            perfdata,
            temp,
            float(OPTIONS.temp_warn),
            float(OPTIONS.temp_crit),
            0.0,
            100.0,
        )

        # load
        perfdata = "{0} 'load'={1};{2};{3};{4};{5}".format(
            perfdata,
            load,
            float(OPTIONS.load_warn),
            float(OPTIONS.load_crit),
            0.0,
            100.0,
        )

        # battery charge
        perfdata = "{0} 'battery_load'={1};{2};{3};{4};{5}".format(
            perfdata,
            batt,
            float(OPTIONS.bat_warn),
            float(OPTIONS.bat_crit),
            0.0,
            100.0
        )

        # battery time
        if OPTIONS.time_warn or OPTIONS.time_crit:
            perfdata = "{0} 'battery_time'={1};{2};{3};;".format(
                perfdata,
                time,
                float(OPTIONS.time_warn),
                float(OPTIONS.time_crit)
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


def get_apcaccess_data():
    """
    Gets the output of apcaccess
    """
    global UPS_INFO

    raw_data = run_cmd("apcaccess -f {0}".format(OPTIONS.file))
    raw_data = raw_data.splitlines()
    for line in raw_data:
        # parse lines to key/value dict
        key = line[: line.find(":")].strip()
        value = line[line.find(":") + 1:].strip()
        LOGGER.debug("Found key '%s' with value '%s'", key, value)
        UPS_INFO[key] = value


if __name__ == "__main__":
    # defines description, version and load parser
    DESC = """%prog is used to check a APC UPS using the apcaccess utility.

  See also: https://github.com/stdevel/check_apcaccess"""
    PARSER = OptionParser(description=DESC, version="%prog version 0.5.1")

    GEN_OPTS = OptionGroup(PARSER, "Generic options")
    MON_OPTS = OptionGroup(PARSER, "Monitoring options")
    THRES_OPTS = OptionGroup(PARSER, "Threshold options")
    PARSER.add_option_group(GEN_OPTS)
    PARSER.add_option_group(MON_OPTS)
    PARSER.add_option_group(THRES_OPTS)

    # -d / --debug
    GEN_OPTS.add_option(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        action="store_true",
        help="enable debugging outputs",
    )

    # -f / --file
    GEN_OPTS.add_option(
        "-f",
        "--file",
        dest="file",
        default="/etc/apcupsd/apcupsd.conf",
        help="apcupsd configuration file (default: /etc/apcupsd/apcupsd.conf)",
    )

    # -P / --enable-perfdata
    MON_OPTS.add_option(
        "-P",
        "--enable-perfdata",
        dest="show_perfdata",
        default=False,
        action="store_true",
        help="enables performance data (default: no)",
    )

    # -w / --temp-warning
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
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
    THRES_OPTS.add_option(
        "-t",
        "--time-warning",
        dest="time_warn",
        type=int,
        metavar="TIME",
        action="store",
        help="battery time left warning threshold (minutes, default: empty)",
    )

    # -T / --time-critical
    THRES_OPTS.add_option(
        "-T",
        "--time-critical",
        dest="time_crit",
        type=int,
        metavar="TIME",
        action="store",
        help="battery time left critical threshold (minutes, default: empty)",
    )

    # -u / --consumption-warning
    THRES_OPTS.add_option(
        "-u",
        "--consumption-warning",
        dest="consum_warn",
        type=int,
        metavar="WATTS",
        action="store",
        help="power consumption warning threshold (watts, default: empty)",
    )

    # -U / --consumption-critical
    THRES_OPTS.add_option(
        "-U",
        "--consumption-critical",
        dest="consum_crit",
        type=int,
        metavar="WATTS",
        action="store",
        help="power consumption critical threshold (watts, default: empty)",
    )

    # parse arguments
    (OPTIONS, ARGS) = PARSER.parse_args()

    # set logger level
    if OPTIONS.debug:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)
    else:
        logging.basicConfig()
        LOGGER.setLevel(logging.INFO)

    # debug outputs
    LOGGER.debug("OPTIONS: %s", OPTIONS)

    # get information and check UPS state
    get_apcaccess_data()
    check_ups()
