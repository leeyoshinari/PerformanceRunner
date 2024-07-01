#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari

import time
import datetime


local_format = "%Y-%m-%d %H:%M:%S"
utc_format = "%Y-%m-%dT%H:%M:%SZ"


def primaryKey():
    return int(time.time() * 10000)


def strfTime():
    return time.strftime(local_format)


def strfDeltaTime(delta=0):
    return time.strftime(local_format, time.localtime(time.time() + delta))


def toTimeStamp(strf_time, delta = 0):
    return time.mktime(time.strptime(strf_time, local_format)) + delta


def utc2local(utc_time: str, gmt: int):
    """
    UTC time to local time.
    UTC time format: 2020-02-02T02:02:02.202002Z, formatting UTC timestamp according to "%Y-%m-%dT%H:%M:%S.%fZ".
    :param utc_time: UTC time
    :param gmt: time zone
    :return: local time
    """
    local_time = datetime.datetime.strptime(utc_time, utc_format) + datetime.timedelta(hours=gmt)
    return local_time.strftime(local_format)


def local2utc(local_time: str, gmt: int):
    """
    Local time to UTC time
    :param local_time: local time
    :param gmt: time zone
    :return: UTC time
    """
    utc_time = datetime.datetime.strptime(local_time, local_format) - datetime.timedelta(hours=gmt)
    return utc_time.strftime(utc_format)


def local_date2utc_date(date_str):
    """
    Convert local date to UTC date
    """
    time_struct = time.strptime(date_str, local_format)
    timestamp = time.mktime(time_struct)
    return time.strftime(utc_format, time.gmtime(timestamp))


def date_to_timestamp(date_str, utc=False):
    if utc:
        time_struct = time.strptime(date_str, utc_format)
    else:
        time_struct = time.strptime(date_str, local_format)
    return time.mktime(time_struct)
