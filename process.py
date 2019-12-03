# -*- coding:gbk -*-
import subprocess


def RunAppiumScript(cmdstring, runtaskid, run_record_id):
    """
    ����Appium�ű���APPIUMʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
    Args:
        cmdstring: �Ѿ���������ƴ�ӵ����
        runtaskid:��������ID
        run_record_id: ���м�¼ID
        core_script_name: ���Ľű�������Ϊ���к��Ľű���֮ǰ����Ҫ���õ�¼�ű�����Ϊ�˽���ͼ�����ֻ��ɺ��Ľű������ڴ˴��룩
    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
        log_info : ��־��Ϣ
    """

    log_info = ""
    cmd_str = cmdstring
    # cmd_str = 'java -jar .\\Script\\AutoTest.jar "%s"' %cmdstring
    print cmd_str

    # fixme xiaorz
    # return 0,"OK","Fake execute successful"


    si = subprocess.STARTUPINFO
    si.wShowWindow = subprocess.SW_HIDE

    proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    proc.wait()

    output_info = proc.stdout.readlines()
    print output_info

    exit_code = proc.returncode
    print exit_code


if __name__ == '__main__':
    RunAppiumScript()
