``check_apcaccess`` is a Nagios / Icinga plugin for checking APC UPS devices using [apcupsd](http://www.apcupsd.com).

# Requirements
The plugin requires a working apcupsd installation - see the [apcupsd online documentation](http://www.apcupsd.org/manual/manual.html) for instructions and valid configuration types.

# Usage
By default, the script checks the UPS temperature, load and battery load. It is possible to control this behaviour by specifying additional parameters (*see below*).
The script also support performance data for data visualization.

The following parameters can be specified:

| Parameter | Description |
|:----------|:------------|
| `-d` / `--debug` | enable debugging outputs (*default: no*) |
| `-h` / `--help` | shows help and quits |
| `-P` / `--show-perfdata` | enables performance data (*default: no*) |
| `-w` / `--temp-warning` | defines temperature warning threshold in Celsius (*default: 50 C*) |
| `-c` / `--temp-critical` | defines temperature critical threshold in Celsius (*default: 50 C*) |
| `-l` / `--load-warning` | defines load warning threshold in percent (*default: 50%*) |
| `-L` / `--load-critical` | defines load critical threshold in percent (*default: 50%*) |
| `-b` / `--battery-warning` | defines battery load warning threshold in percent (*default: 80%*) |
| `-B` / `--battery-critical` | defines battery load critical threshold in percent (*default: 50%*) |
| `-t` / `--time-warning` | defines battery time left warning threshold in minutes (*default: empty*) |
| `-T` / `--time-critical` | defines battery time left critical threshold in minutes (*default: empty*) |
| `-u` / `--consumption-warning` | defines power consumption warning threshold in watts (*default: empty*) |
| `-U` / `--consumption-critical` | defines power consumption critical threshold in watts (*default: empty*) |
| `--version` | prints programm version and quits |

## Examples
The following example checks major metrics of a connected UPS:
```
$ ./check_apcaccess.py
OK: temperature okay (34.0), load okay (39.0), battery load okay (100.0)
```

Also checking battery time and power consumption:
```
$ ./check_apcaccess.py -t 20 -T 10 -u 100 -U 150
OK: temperature okay (34.0), load okay (34.0), battery load okay (100.0), battery time okay (28.0), power consumption okay (78.2)
```

Reporting performance data:
```
$ ./check_apcaccess.py -P
OK: temperature okay (34.0), load okay (35.0), battery load okay (100.0) | 'consumption'=80.5 'temperature'=34.0;50.0;60.0;0.0;100.0 'load'=35.0;50.0;80.0;0.0;100.0 'battery_load'=100.0;80.0;50.0;0.0;100.0
```

# Installation
To install the plugin, move the Python script into the appropriate directory and create a **NRPE configuration**.

# Configuration
Inside Nagios / Icinga you will need to configure a remote check command, e.g. for NRPE:
```
#check_nrpe_apcaccess
define command{
    command_name        check_nrpe_apcaccess
    command_line        $USER1$/check_nrpe -H $HOSTADDRESS$ -c check_apcaccess -a $ARG1$
}
```

Configure the check for a particular host, e.g.:
```
#DIAG: Updates
define service{
        use                             generic-service
        host_name                       st-ipfire02
        service_description             DIAG: APC UPS
        check_command                   check_nrpe_apcaccess!-P
}
```
