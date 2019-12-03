# -*- coding:gbk -*-
import gl
import threading
import commFuncs as cF
import time
import datetime
import signal

is_exit = False
class timeTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__ (self)
        
    def comparetime(self,now,crontab):
        
        for i,item in enumerate(crontab):
            if item == '*':
                continue
            if item == now[i]:
                continue
            else:
                return -1
        return 0
    def run(self):
        while is_exit != True:
            #每隔一分钟读取一次定时任务表，匹配的任务就直接加入到立即任务表中
            now = datetime.datetime.now()
            nowtab = (str(now.minute),str(now.hour),str(now.day),str(now.month),str(now.weekday()))
            print nowtab
            sql = 'select * from sx_timed_task'
            ds = cF.executeCaseSQL(sql)
            for rec in ds:
                crontab = (rec['MINUTE'],rec['HOUR'],rec['DAY'],rec['MONTH'],rec['WEEK'])
                if self.comparetime(nowtab,crontab) == 0:
                    #加入任务表
                    print "add task table"

            time.sleep(60)
        pass

def processTerm(signum, frame):
    global is_exit
    is_exit = True
def main():
    signal.signal(signal.SIGINT, processTerm)
    signal.signal(signal.SIGTERM, processTerm)

    

    time_task = timeTask()
    time_task.setDaemon(True)
    time_task.start()
    while True:
        if time_task.isAlive() == False:
            break;

if __name__=='__main__':
    cF.readConfigFile()
    main()