#coding=gbk
import subprocess

def RunSeleniumScript():
    """
    运行Selenium脚本，Selenium使用了统一的一个脚本，通过参数的传递来调用相关功能。
    Args:
        system_id: 系统ID
        funcid: 已经经过参数拼接的命令串
        param_data_id: 用例步骤数据id
        runtaskid:运行任务ID
        CASE_NAME:案例名称
        run_record_id: 运行记录ID

    Returns:
        一个元组（ret，msg）：
        ret : 0 表示 成功，-1 表示 失败
        msg : 对应信息
        log_info : 日志信息
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