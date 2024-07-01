#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: leeyoshinari
import time
import logging
import traceback
from django.conf import settings
from common.generator import strfDeltaTime, local_date2utc_date, date_to_timestamp

logger = logging.getLogger('django')


def draw_data_from_db(room, group, host, startTime=None, endTime=None):
    """
    Get data from InfluxDB, and visualize
    :param host: client IP, required
    :param startTime: Start time; optional
    :param endTime: end time; optional
    :return:
    """
    post_data = {
        'time': '',
        'cpu_time': [],
        'cpu': [],
        'iowait': [],
        'usr_cpu': [],
        'mem': [],
        'mem_available': [],
        'jvm': [],
        'disk': [],
        'disk_r': [],
        'disk_w': [],
        'disk_d': [],
        'rec': [],
        'trans': [],
        'net': [],
        'tcp': [],
        'retrans': [],
        'port_tcp': [],
        'close_wait': [],
        'time_wait': [],
    }

    res = {'code': 0, 'flag': 1, 'msg': 'Successful!'}

    try:
        if not startTime:     # If there is a start time and an end time
            startTime = strfDeltaTime(-600)
        exclusive_time = startTime
        if 'T' not in startTime:
            startTime = local_date2utc_date(startTime)
        s_time = time.time()
        if host != 'all':
            if endTime:
                endTime = local_date2utc_date(endTime)
                sql = f'''
                        from(bucket: "{settings.MONITOR_BUCKET}")
                            |> range(start: {startTime}, stop: {endTime})
                            |> filter(fn: (r) => r._measurement == "server_{group}" and r.room == "{room}" and r.host == "{host}")
                            |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                            |> keep(columns: ["_time","cpu","iowait","mem","mem_available","jvm","disk","disk_r","disk_w","rec","trans","net","tcp","retrans","port_tcp","close_wait","time_wait"])
                        '''
            else:
                sql = f'''
                        from(bucket: "{settings.MONITOR_BUCKET}")
                            |> range(start: {startTime})
                            |> filter(fn: (r) => r._measurement == "server_{group}" and r.room == "{room}" and r.host == "{host}")
                            |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                            |> keep(columns: ["_time","cpu","iowait","mem","mem_available","jvm","disk","disk_r","disk_w","rec","trans","net","tcp","retrans","port_tcp","close_wait","time_wait"])
                        '''
        else:
            if endTime:
                endTime = local_date2utc_date(endTime)
                sql = f'''
                        from(bucket: "{settings.MONITOR_BUCKET}")
                            |> range(start: {startTime}, stop: {endTime})
                            |> filter(fn: (r) => r._measurement == "server_{group}" and r.room == "{room}")
                            |> window(every: {settings.SAMPLING_INTERVAL}s)
                            |> mean(column: "_value")
                            |> duplicate(column: "_stop", as: "_time")
                            |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                            |> keep(columns: ["_time","cpu","iowait","mem","mem_available","jvm","disk","disk_r","disk_w","rec","trans","net","tcp","retrans","port_tcp","close_wait","time_wait"])
                        '''
            else:
                sql = f'''
                        from(bucket: "{settings.MONITOR_BUCKET}")
                            |> range(start: {startTime})
                            |> filter(fn: (r) => r._measurement == "server_{group}" and r.room == "{room}")
                            |> window(every: {settings.SAMPLING_INTERVAL}s)
                            |> mean(column: "_value")
                            |> duplicate(column: "_stop", as: "_time")
                            |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                            |> keep(columns: ["_time","cpu","iowait","mem","mem_available","jvm","disk","disk_r","disk_w","rec","trans","net","tcp","retrans","port_tcp","close_wait","time_wait"])
                        '''
        logger.info(f'Execute sql: {sql}')
        datas = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
        if datas:
            for data in datas:
                for record in data.records:
                    date_t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(record.values['_time'] / 1000000000)))
                    if date_t == exclusive_time: continue
                    post_data['cpu_time'].append(date_t)
                    post_data['cpu'].append(record.values['cpu'])
                    post_data['iowait'].append(record.values['iowait'])
                    # post_data['usr_cpu'].append(record.values['usr_cpu'])
                    post_data['mem'].append(record.values['mem'])
                    post_data['mem_available'].append(record.values['mem_available'])
                    post_data['jvm'].append(record.values['jvm'])
                    post_data['disk'].append(record.values['disk'])
                    post_data['disk_r'].append(record.values['disk_r'])
                    post_data['disk_w'].append(record.values['disk_w'])
                    # post_data['disk_d'].append(record.values['disk_d'])
                    post_data['rec'].append(record.values['rec'])
                    post_data['trans'].append(record.values['trans'])
                    post_data['net'].append(record.values['net'])
                    post_data['tcp'].append(record.values['tcp'])
                    post_data['retrans'].append(record.values['retrans'])
                    post_data['port_tcp'].append(record.values['port_tcp'])
                    post_data['close_wait'].append(record.values['close_wait'])
                    post_data['time_wait'].append(record.values['time_wait'])
            post_data['time'] = post_data['cpu_time'][-1]

        else:
            res['msg'] = 'No monitoring data is found, please check the time setting.'
            res['code'] = 1

        res.update({'post_data': post_data})
        logger.info(f'Time consuming to query is {time.time() - s_time}')

    except Exception as err:
        logger.error(traceback.format_exc())
        res['msg'] = str(err)
        res['code'] = 1

    del post_data
    return res


def get_lines(datas):
    """
    Calculate percentile
    :param datas
    :return:
    """
    cpu = datas['cpu']
    disk_r = datas['disk_r'] if datas['disk_r'] else [-1]
    disk_w = datas['disk_w'] if datas['disk_w'] else [-1]
    io = datas['io']
    rec = datas['rec'] if datas['rec'] else [-1]
    trans = datas['trans'] if datas['trans'] else [-1]
    nic = datas['nic']

    cpu.sort()
    disk_r.sort()
    disk_w.sort()
    io.sort()
    rec.sort()
    trans.sort()
    nic.sort()

    line75 = [round(cpu[int(len(cpu) * 0.75)], 2), round(disk_r[int(len(disk_r) * 0.75)], 2),
              round(disk_w[int(len(disk_w) * 0.75)], 2), round(io[int(len(io) * 0.75)], 3),
              round(rec[int(len(rec) * 0.75)], 2), round(trans[int(len(trans) * 0.75)], 2),
              round(nic[int(len(nic) * 0.75)], 3)]
    line90 = [round(cpu[int(len(cpu) * 0.9)], 2), round(disk_r[int(len(disk_r) * 0.9)], 2),
              round(disk_w[int(len(disk_w) * 0.9)], 2), round(io[int(len(io) * 0.9)], 3),
              round(rec[int(len(rec) * 0.9)], 2), round(trans[int(len(trans) * 0.9)], 2),
              round(nic[int(len(nic) * 0.9)], 3)]
    line95 = [round(cpu[int(len(cpu) * 0.95)], 2), round(disk_r[int(len(disk_r) * 0.95)], 2),
              round(disk_w[int(len(disk_w) * 0.95)], 2), round(io[int(len(io) * 0.95)], 3),
              round(rec[int(len(rec) * 0.95)], 2), round(trans[int(len(trans) * 0.95)], 2),
              round(nic[int(len(nic) * 0.95)], 3)]
    line99 = [round(cpu[int(len(cpu) * 0.99)], 2), round(disk_r[int(len(disk_r) * 0.99)], 2),
              round(disk_w[int(len(disk_w) * 0.99)], 2), round(io[int(len(io) * 0.99)], 3),
              round(rec[int(len(rec) * 0.99)], 2), round(trans[int(len(trans) * 0.99)], 2),
              round(nic[int(len(nic) * 0.99)], 3)]

    return {'line': [line75, line90, line95, line99]}


def query_nginx_detail_summary(group_key, source, order_key, order_by, start_time, end_time, limit_num, path):
    res = {'code': 0, 'msg': 'Successful!'}
    try:
        post_data = []
        if not start_time:
            start_time = strfDeltaTime(-600)
        if not end_time:
            end_time = strfDeltaTime()
        if 'T' not in start_time:
            start_time = local_date2utc_date(start_time)
        if 'T' not in end_time:
            end_time = local_date2utc_date(end_time)
        s_time = time.time()
        if path:
            path = path.replace('/', '\/')
            sql = f'''
                    from(bucket: "{settings.NGINX_BUCKET}")
                        |> range(start: {start_time}, stop: {end_time})
                        |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}" and r.path =~ /{path}/)
                        |> filter(fn: (r) => r["_field"] == "rt" or r["_field"] == "size" or r["_field"] == "error")
                        |> aggregateWindow(every: 10000d, fn: sum)
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> group(columns: ["path"], mode: "by")
                    '''
            data_details = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
            if data_details:
                sql = f'''
                            from(bucket: "{settings.NGINX_BUCKET}")
                                |> range(start: {start_time}, stop: {end_time})
                                |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}" and r.path =~ /{path}/)
                                |> filter(fn: (r) => r["_field"] == "rt")
                                |> aggregateWindow(every: 10000d, fn: count)
                                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                                |> group(columns: ["path"], mode: "by")
                            '''
                data_counts = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
        else:
            sql = f'''
                    from(bucket: "{settings.NGINX_BUCKET}")
                        |> range(start: {start_time}, stop: {end_time})
                        |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}")
                        |> filter(fn: (r) => r["_field"] == "rt" or r["_field"] == "size" or r["_field"] == "error")
                        |> aggregateWindow(every: 10000d, fn: sum)
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> group(columns: ["path"], mode: "by")
                    '''
            data_details = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
            if data_details:
                sql = f'''
                        from(bucket: "{settings.NGINX_BUCKET}")
                            |> range(start: {start_time}, stop: {end_time})
                            |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}")
                            |> filter(fn: (r) => r["_field"] == "rt")
                            |> aggregateWindow(every: 10000d, fn: count)
                            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                            |> group(columns: ["path"], mode: "by")
                        '''
                data_counts = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
        logger.debug(f'Execute sql: {sql}')
        data_count = {}
        duration = date_to_timestamp(end_time, utc=True) - date_to_timestamp(start_time, utc=True)
        if data_details:
            for data in data_counts:
                for record in data.records:
                    data_count.update({record.values['path']: record.values['rt']})
            for data in data_details:
                for record in data.records:
                    post_data.append({'path': record.values['path'], 'sample': data_count[record.values['path']],
                                      'qps': data_count[record.values['path']]/duration, 'rt': record.values['rt'],
                                      'size': record.values['size']/1048576, 'error': record.values['error']})
        else:
            res['msg'] = 'No Nginx summary data is found, please check it again.'
            res['code'] = 1
        post_data.sort(key=lambda x: (-x[order_key]))
        res.update({'data': post_data[:limit_num]})
        del data_count
        logger.info(f'Time consuming to query is {time.time() - s_time}')
    except:
        logger.error(traceback.format_exc())
        res['msg'] = 'Query Nginx summary data error, please check it again ~'
        res['code'] = 1

    del post_data
    return res


def query_nginx_detail_by_path(group_key, source, path, start_time, end_time):
    post_data = {
        'time': '',
        'c_time': [],
        'qps': [],
        'rt': [],
        'size': [],
        'error': []
    }
    res = {'code': 0, 'msg': 'Successful!'}
    try:
        if not start_time:
            start_time = strfDeltaTime(-600)
        if not end_time:
            end_time = strfDeltaTime()
        exclusive_time = start_time
        if 'T' not in start_time:
            start_time = local_date2utc_date(start_time)
        end_time = local_date2utc_date(end_time)
        s_time = time.time()
        sql = f'''
                from(bucket: "{settings.NGINX_BUCKET}")
                    |> range(start: {start_time}, stop: {end_time})
                    |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}" and r.path == "{path}")
                    |> filter(fn: (r) => r["_field"] == "rt" or r["_field"] == "size" or r["_field"] == "error")
                    |> aggregateWindow(every: 1s, fn: sum, createEmpty: true)
                    |> fill(column: "error", value: 0)
                    |> fill(column: "rt", value: 0.0)
                    |> fill(column: "size", value: 0)
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                '''
        data_details = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
        if data_details:
            sql = f'''
                    from(bucket: "{settings.NGINX_BUCKET}")
                        |> range(start: {start_time}, stop: {end_time})
                        |> filter(fn: (r) => r._measurement == "nginx_{group_key}" and r.source == "{source}" and r.path == "{path}")
                        |> filter(fn: (r) => r["_field"] == "rt")
                        |> aggregateWindow(every: 1s, fn: count, createEmpty: true)
                        |> fill(column: "_value", value: 0)
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> map(fn: (r) => ({{ r with _time: uint(v: r._time) }}))
                    '''
            data_counts = settings.INFLUX_QUERY.query(org=settings.INFLUX_ORG, query=sql)
        logger.debug(f'Execute sql: {sql}')
        data_count = {}
        if data_details:
            for data in data_counts:
                for record in data.records:
                    data_count.update({str(int(record.values['_time']/1000000000)): record.values['rt'] if record.values['rt'] else 0})
            for data in data_details:
                for record in data.records:
                    t = int(record.values['_time']/1000000000)
                    date_t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
                    if date_t == exclusive_time: continue
                    post_data['c_time'].append(date_t)
                    post_data['qps'].append(data_count[str(t)])
                    post_data['rt'].append(record.values['rt'] if record.values['rt'] else 0)
                    post_data['size'].append(record.values['size']/1048576 if record.values['size'] else 0)
                    post_data['error'].append(record.values['error'] if record.values['error'] else 0)
            post_data['time'] = post_data['c_time'][-1]
        else:
            res['msg'] = 'No Nginx data is found, please check it again.'
            res['code'] = 1
        res.update({'data': post_data})
        del data_count
        logger.info(f'Time consuming to query is {time.time() - s_time}')
    except:
        logger.error(traceback.format_exc())
        res['msg'] = 'Query Nginx data error, please check it again ~'
        res['code'] = 1

    del post_data
    return res
