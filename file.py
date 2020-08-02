
import os
from queue import Queue
 
class file():
    def __init__(self):
        self.__queue = Queue()

    def SetPath(self,path):
        self.__path = path
    
    def GetPath(self):
        return self.__path

    def GetSize(self):
        fsize = os.path.getsize(self.__path)
        fsize = fsize/float(1024)
        return round(fsize, 2) 

    #打开文件读取数据
    def Read(self):
        self.__queue.clear()
        file_content = None
        try:
            f = open(self.__path,"rb")    #直接以二进制读入，传输时不用encode和decode了
            file_content = f.read()
            f.close()
        except Exception as ret:
            print("没有此文件")



    


 
