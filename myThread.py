import threading

class MyThread (threading.Thread):
    def __init__(self, name, process, args = None):
        threading.Thread.__init__(self)
        self.args = args
        self.name = name
        self.process = process

    # 实现函数重载
    def run(self):
        print ("thread start：" + self.name)
        if not self.args:
            self.process()
        elif type(self.args) == list:
            L = len(self.args)
            if L == 2:
                self.process(self.args[0],self.args[1])
            elif L == 3:
                self.process(self.args[0],self.args[1],self.args[2])
            else:
                self.process(self.args[0],self.args[1],self.args[2],self.args[3])
        else:
            self.process(self.args)
        print ("thread end：" + self.name)