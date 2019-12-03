# -*- coding:gbk -*-
import subprocess


def RunAppiumScript(cmdstring, runtaskid, run_record_id):
    """
    运行Appium脚本，APPIUM使用了统一的一个脚本，通过参数的传递来调用相关功能。
    Args:
        cmdstring: 已经经过参数拼接的命令串
        runtaskid:运行任务ID
        run_record_id: 运行记录ID
        core_script_name: 核心脚本名（因为运行核心脚本名之前，需要调用登录脚本名，为了将截图的名字换成核心脚本名，在此传入）
    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
        log_info : 日志信息
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
