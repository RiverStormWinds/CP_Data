#coding=gbk
import subprocess

def RunSeleniumScript():
    """
    ����Selenium�ű���Seleniumʹ����ͳһ��һ���ű���ͨ�������Ĵ�����������ع��ܡ�
    Args:
        system_id: ϵͳID
        funcid: �Ѿ���������ƴ�ӵ����
        param_data_id: ������������id
        runtaskid:��������ID
        CASE_NAME:��������
        run_record_id: ���м�¼ID

    Returns:
        һ��Ԫ�飨ret��msg����
        ret : 0 ��ʾ �ɹ���-1 ��ʾ ʧ��
        msg : ��Ӧ��Ϣ
        log_info : ��־��Ϣ
    """
    output_info_list = []
    log_info = ""

    cmd_str = "java -jar .\Script\JZYYAutoTest.jar 9990050082 14158"

    try:
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=True,
                                startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)

        while proc.poll() is None:
            line = proc.stdout.readline()
            line = line.strip()
            if line:
                output_info_list.append(line)
    except BaseException, ex:
        pass

if __name__ == '__main__':
    RunSeleniumScript()