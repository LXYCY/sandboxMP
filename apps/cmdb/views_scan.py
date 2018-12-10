# @Time   : 2018/12/4 20:07
# @Author : RobbieHan
# @File   : views_scan.py

import ast
import time
import logging
from ruamel import yaml

from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from system.mixin import LoginRequiredMixin
from custom import BreadcrumbMixin, SandboxListView, SandboxDeleteView
from utils.sandbox_utils import ConfigFileMixin
from system.models import Menu
from .models import DeviceScanInfo
from .tasks import scan_execution

error_logger = logging.getLogger('sandbox_error')


class ScanConfigView(LoginRequiredMixin, BreadcrumbMixin, ConfigFileMixin, View):

    def get(self, request):
        menu = Menu.get_menu_by_request_url(request.path_info)
        template_name = 'cmdb/scan_config.html'
        context = self.get_conf_content()
        context.update(menu)
        return render(request, template_name, context)

    def post(self, request):
        ret = dict(result=False)
        config = dict()
        hosts = request.POST
        try:
            config['net_address'] = ast.literal_eval(hosts['net_address'])
            config['ssh_username'] = hosts['ssh_username']
            config['ssh_port'] = hosts['ssh_port']
            config['ssh_password'] = hosts['ssh_password']
            config['ssh_private_key'] = hosts['ssh_private_key']
            config['commands'] = ast.literal_eval(hosts['commands'])
            config['auth_type'] = hosts['auth_type']
            config['scan_type'] = hosts['scan_type']
            config['email'] = hosts['email']
            config['send_email'] = hosts['send_email']
            data = dict(hosts=config)
            config_file = self.get_config_file()
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, Dumper=yaml.RoundTripDumper, indent=4)
                ret['result'] = True
        except Exception as e:
            error_logger.error(e)

        return JsonResponse(ret)


class DeviceScanView(LoginRequiredMixin, BreadcrumbMixin, TemplateView):
    template_name = 'cmdb/device_scan.html'


class DeviceScanExecView(LoginRequiredMixin, View):

    def get(self, request):
        scan_execution.delay()
        # scan_execution.apply_async()
        return JsonResponse({'result': True, 'msg': '扫描任务已下发'})


class DeviceScanListView(SandboxListView):
    model = DeviceScanInfo
    fields = ['id', 'sys_hostname', 'hostname', 'mac_address', 'auth_type', 'status', 'os_type', 'device_type']


class DeviceScanDetailView(LoginRequiredMixin, View):

    def get(self, request):
        ret = Menu.get_menu_by_request_url(request.path_info)
        if 'id' in request.GET and request.GET['id']:
            device = get_object_or_404(DeviceScanInfo, pk=int(request.GET['id']))
            ret['device'] = device
        return render(request, 'cmdb/device_scan_detail.html', ret)


class DeviceScanDeleteView(SandboxDeleteView):
    model = DeviceScanInfo


