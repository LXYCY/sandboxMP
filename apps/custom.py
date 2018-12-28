# @Time   : 2018/11/9 22:06
# @Author : RobbieHan
# @File   : custom.py

import json
import re

from django.views.generic import CreateView, UpdateView, View
from django.shortcuts import HttpResponse
from django.http import Http404, JsonResponse
from django.db.models.query import QuerySet
from django.core.exceptions import ImproperlyConfigured

from system.mixin import LoginRequiredMixin
from system.models import Menu


class BreadcrumbMixin:

    def get_context_data(self, **kwargs):
        menu = Menu.get_menu_by_request_url(url=self.request.path_info)
        if menu is not None:
            kwargs.update(menu)
        return super().get_context_data(**kwargs)


class SandboxGetObjectMixin:

    def get_object(self, queryset=None):

        if queryset is None:
            queryset = self.get_queryset()
        if 'id' in self.request.GET and self.request.GET['id']:
            queryset = queryset.filter(id=int(self.request.GET['id']))
        elif 'id' in self.request.POST and self.request.POST['id']:
            queryset = queryset.filter(id=int(self.request.POST['id']))
        else:
            raise AttributeError("Generic detail view %s must be called with id. "
                                 % self.__class__.__name__)
        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No %(verbose_name)s found matching the query" %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj


class SandboxMultipleObjectMixin:

    fields = []
    search_fields = []
    queryset = None
    model = None

    def get_queryset(self):
        if self.queryset is not None:
            queryset = self.queryset
        elif self.queryset is None and self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define %(cls)s.model, %(cls)s.queryset."
                % {'cls': self.__class__.__name__}
            )
        return queryset

    def get_datatables_paginator(self, request):

        datatables = request.GET
        draw = int(datatables['draw'])
        start = int(datatables['start'])
        length = int(datatables['length'])
        order_column = datatables['order[0][column]']
        order_dir = datatables['order[0][dir]']
        order_field = datatables['columns[{}][data]'.format(order_column)]
        search_value = datatables['search[value]']
        queryset = self.get_queryset()
        fields = self.get_fields()

        if search_value:
            q = self.get_q(search_value)
            queryset = queryset.filter(q)

        if order_dir == 'asc':
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by('-{0}'.format(order_field))

        record_total_count = queryset.count()
        queryset = queryset.values(*self.fields)

        record_filter_count = queryset.count()
        object_list = queryset[start: (start + length)]
        data = list(object_list)

        return {
            'draw': draw,
            'recordsTotal': record_total_count,
            'recordsFiltered': record_filter_count,
            'data': data,
        }
    
    def get_fields(self):
        if self.fields:
            fields = self.fields
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing fields."
                % {'cls': self.__class__.__name__}
            )
        return fields
    
    def get_q(self, search_value):
        search_fields = self.search_fields
        q = Q()
        q.connector = 'OR'
        for field in search_fields:
            q.children.append((field + '__icontains', search_value))
        return q


class SandboxEditViewMixin:

    def post(self, request, *args, **kwargs):
        res = dict(result=False)
        form = self.get_form()
        if form.is_valid():
            form.save()
            res['result'] = True
        else:
            pattern = '<li>.*?<ul class=.*?><li>(.*?)</li>'
            form_errors = str(form.errors)
            errors = re.findall(pattern, form_errors)
            res['error'] = errors[0]
        return HttpResponse(json.dumps(res), content_type='application/json')


class SandboxCreateView(LoginRequiredMixin, SandboxEditViewMixin, CreateView):
    """"
    View for create an object, with a response rendered by a template.
    Returns information with Json when the data is created successfully or fails.
    """


class SandboxUpdateView(LoginRequiredMixin, SandboxEditViewMixin, SandboxGetObjectMixin, UpdateView):
    """
    View for updating an object, with a response rendered by a template.
    """
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


class SandboxListView(LoginRequiredMixin, SandboxMultipleObjectMixin, View):
    """
    JsonResponse some json of objects, set by `self.model` or `self.queryset`.
    """
    def get(self, request):
        context = self.get_datatables_paginator(request)
        return JsonResponse(context)


class SandboxDeleteView(LoginRequiredMixin, SandboxMultipleObjectMixin, View):

    def post(self, request):
        context = dict(result=False)
        queryset = self.get_queryset()
        if 'id' in request.POST and request.POST['id']:
            id_list = map(int, request.POST['id'].split(','))
            queryset.filter(id__in=id_list).delete()
            context['result'] = True
        else:
            raise AttributeError("Sandbox delete view %s must be called with id. "
                                 % self.__class__.__name__)
        return JsonResponse(context)

