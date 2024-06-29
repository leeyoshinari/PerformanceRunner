#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: leeyoshinari

import os
import time
import logging
import traceback
from django.db.models.deletion import ProtectedError
from django.conf import settings
from .models import TestPlan, ThreadGroup, TransactionController
from .models import HTTPRequestHeader, HTTPSampleProxy, PerformanceTestTask
from .taskViews import start_test, stop_test, change_tps_test
from .common.fileController import delete_local_file
from common.Result import result
# Create your views here.


logger = logging.getLogger('django')


def delete_file_from_disk(file_path):
    path_list = file_path.split('/')
    if settings.FILE_STORE_TYPE == '0':
        try:
            file_folder = os.path.join(settings.FILE_ROOT_PATH, path_list[-2])
            file_local_path = os.path.join(file_folder, path_list[-1])
            os.remove(file_local_path)
            _ = delete_local_file(file_folder)
        except FileNotFoundError:
            logger.warning(f"FileNotFound: No such file: {file_path}")
    else:
        settings.MINIO_CLIENT.delete_file(path_list[-2], path_list[-1])


def delete(request):
    if request.method == 'POST':
        try:
            username = request.user.username
            ip = request.headers.get('x-real-ip')
            delete_type = request.POST.get('type')
            delete_id = request.POST.get('id')
            if delete_type == 'plan':
                plan = TestPlan.objects.get(id=delete_id)
                if plan.is_file == 1:
                    delete_file_from_disk(plan.file_path)
                plan.delete()
            if delete_type == 'group':
                group = ThreadGroup.objects.get(id=delete_id)
                if group.file:
                    file_path = group.file.get('file_path')
                    delete_file_from_disk(file_path)
                group.delete()
            if delete_type == 'controller':
                TransactionController.objects.get(id=delete_id).delete()
            if delete_type == 'sample':
                HTTPSampleProxy.objects.get(id=delete_id).delete()
            if delete_type == 'header':
                HTTPRequestHeader.objects.get(id=delete_id).delete()
            if delete_type == 'task':
                task = PerformanceTestTask.objects.get(id=delete_id)
                if task.path:
                    delete_file_from_disk(task.path)
                task.delete()
            logger.info(f'{delete_type} {delete_id} is deleted success, operator: {username}, IP: {ip}')
            return result(msg='Delete success ~')
        except ProtectedError:
            logger.error(traceback.format_exc())
            return result(code=1, msg='Delete failure, because it is referenced through protected foreign keys ~')
        except:
            logger.error(traceback.format_exc())
            return result(code=1, msg='Delete failure ~')


def is_valid(request):
    if request.method == 'POST':
        try:
            username = request.user.username
            ip = request.headers.get('x-real-ip')
            set_type = request.POST.get('set_type')
            set_id = request.POST.get('id')
            is_valid = request.POST.get('is_valid')
            if set_type == 'plan':
                res = TestPlan.objects.get(id=set_id)
            if set_type == 'group':
                res = ThreadGroup.objects.get(id=set_id)
            if set_type == 'controller':
                res = TransactionController.objects.get(id=set_id)
            if set_type == 'sample':
                res = HTTPSampleProxy.objects.get(id=set_id)
            res.is_valid = is_valid
            res.operator = username
            res.save()
            logger.info(f'{set_type} {set_id} status is set to {is_valid} success, operator: {username}, IP: {ip}')
            return result(msg='Set success ~')
        except:
            logger.error(traceback.format_exc())
            return result(code=1, msg='Set failure ~')


def request_auto_run(request):
    if request.method == 'GET':
        username = request.user.username
        ip = request.headers.get('x-real-ip')
        tasks = PerformanceTestTask.objects.filter(plan__schedule=1, status=0)
        logger.info(f'Total auto test task is {len(tasks)}')
        for task in tasks:
            index = 0
            total_index = len(task.plan.time_setting) - 1
            for timing in task.plan.time_setting:
                if index == 0:
                    settings.SCHEDULER.add_job(start_test, 'date', run_date=timing['timing'], args=[task.id, None, username, ip], id=f"{task.id}_{index}")
                elif index == total_index:
                    settings.SCHEDULER.add_job(stop_test, 'date', run_date=timing['timing'], args=[task.id, 'all', username, ip], id=f"{task.id}_{index}")
                else:
                    settings.SCHEDULER.add_job(change_tps_test, 'date', run_date=timing['timing'], args=[task.id, 'all', timing['value'], username, ip], id=f"{task.id}_{index}")
        logger.info(f'Auto run performance test task success, operator: {username}, IP: {ip}')
        return result(msg='success')


# def cancel_auto_task(request):

