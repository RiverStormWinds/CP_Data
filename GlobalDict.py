# -*- coding:gbk -*-
_global_dict={}
def _init():#��ʼ��
    global _global_dict
    _global_dict = {}


def set_value(key,value):
    """ ����һ��ȫ�ֱ��� """
    _global_dict[key] = value


def get_value(key,defValue=None):
    """ ���һ��ȫ�ֱ���,�������򷵻�Ĭ��ֵ """
    try:
        return _global_dict[key]
    except KeyError:
        return defValue
