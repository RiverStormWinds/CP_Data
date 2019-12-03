# -*-coding:utf-8-*-
from time import ctime
import threading
import collections
import time
loops = ['广州', '北京']
t_list = ['01', '02', '03']
cldas_sum = collections.deque()


class MyThread(threading.Thread):
    def __init__(self, func, args, name=''):
        threading.Thread.__init__(self)
        self.name = name
        self.func = func
        self.args = args
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception:
            return None


def loop(nloop):
    for j in t_list:
        cldas_values = []
        for k in range(4):
            cldas_value = nloop + str(k)
            cldas_values.append(cldas_value)
        cldas_values.append(j)
        cldas_values.append(nloop)
        cldas_sum.append(cldas_values)
        print(id(cldas_values))
    print "123456"
    time.sleep(10)
    return cldas_sum


def main():
    print('start at', ctime())
    threads = []
    nloops = range(len(loops))
    for i in nloops:
        t = MyThread(loop, (loops[i],), loop.__name__)
        threads.append(t)
    for i in nloops:  # start threads 此处并不会执行线程，而是将任务分发到每个线程，同步线程。等同步完成后再开始执行start方法
        threads[i].start()
    for i in nloops:  # jion()方法等待线程完成
        threads[i].join()
    for i in range(len(threads)):
        print(threads[i].get_result())
    print('DONE AT:', ctime())


   # def test(self, run_test_json_str, num):
   #      # t = MyThreadRunTest(self.run_test, (run_test_json_str,), self.run_test.__name__)
   #      run_test_json_str = json.loads(run_test_json_str)
   #      run_test_json_str = [run_test_json_str[i:i + int(num)] for i in range(0, len(run_test_json_str), int(num))]
   #      threads = []
   #      nloops = range(len(run_test_json_str))
   #      for i in nloops:
   #          t = MyThreadRunTest(self.run_test, (run_test_json_str[i],), self.run_test.__name__)
   #          threads.append(t)
   #      for i in nloops:  # start threads 此处并不会执行线程，而是将任务分发到每个线程，同步线程。等同步完成后再开始执行start方法
   #          threads[i].start()
   #      for i in nloops:  # jion()方法等待线程完成
   #          threads[i].join()
   #      result = []
   #      for i in range(len(threads)):
   #          result.append(threads[i].get_result())
   #      return result
if __name__ == '__main__':
    main()