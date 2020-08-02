import socket
from PyQt5 import QtCore
from myThread import MyThread
from protocol import Frame
import threading
import time
import winreg
import os
import math
from PyQt5.QtWidgets import *

# 获取桌面路径
def GetDesktopPath():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    return winreg.QueryValueEx(key, "Desktop")[0]


class Client(QtCore.QObject):
    connect_cnt_signal = QtCore.pyqtSignal(int)             # 向ui发一个信号，更新状态栏连接数
    transfer_pbar_signal = QtCore.pyqtSignal(int,int,int)   # 向ui发送一个信号，更新下载窗口中的进度
    pbar_create_signal = QtCore.pyqtSignal(int,str,int)     # 向ui发送一个信号，创建下载窗口


    def __init__(self,TransPorter):
        super().__init__()
        self.__client_is_working = False            # client正在工作标志
        self.__TransPorter = TransPorter

        self.__server_desktop = ''                  # 服务器的桌面路径
        self.__server_disk_c = 'C:/'                # 服务器的C盘路径

        self.__dir_floder = []                      # 服务器某路径下的目录列表
        self.__dir_files = []                       # 服务器某路径下的文件列表
        self.__dir_sizes = []                       # 服务器某路径下的文件尺寸列表

        self.__socket = None                        # 当前服务器用于刷新UI的socket (client主线程的socket)             
        self.__frame = Frame()                      # 当前服务器用于刷新UI的frame  (client主线程的frame) 
        self.__connetion_cnt = 0                    # 当前服务器的文件传输线程数目

        self.__sub_thread = dict()                  # 元素：(线程名:[Frame对象,thread对象,socket对象])
        self.__ID = ''                              # 客户端ID
        self.__save_dir = GetDesktopPath()          # 下载文件的保存路径(默认为桌面路径)

        self.__last_connection = True               # 当前没有连接
    def SetDestServer(self,port,ip):
        self.__port = port
        self.__ip = ip  

    def ClientStart(self):
        self.__client_is_working = True

    def ClientShutDown(self):
        self.__client_is_working = False
        self.__connetion_cnt = 0
        if self.__socket:
            self.__socket.close()

        self.connect_cnt_signal.emit(0)     # 更新UI
        self.__last_connection = True
    
    def IsNotConnecting(self):
        return self.__last_connection

    def GetDesktopPath(self):
        return self.__server_desktop
    
    def GetConnectionCnt(self):
        return self.__connetion_cnt

    def SetSaveDir(self,dir):
        self.__save_dir = dir

    def IsDir(self,path):
        if path in self.__dir_floder:
            return True
        return False
                                                                    
    # 用于数据收发的基础方法----------------------------------------------------------------------
    # socket接收字节流
    def BytesRecv(self,client_socket,max_size):
        data = None
        while data == None and self.__client_is_working:      
            try:
                data = client_socket.recv(max_size)
            except BlockingIOError:                     # 非阻塞socket，pass此异常以实现轮询
                pass
            except ConnectionResetError:                # 服务器断开了
                self.__client_is_working = False
                return '连接断开'
            except socket.timeout:
                self.__client_is_working = False
                return '连接断开'            
        
        if not self.__client_is_working or data == '':  # 如果是服务器断开，返回空字符串
            return '连接断开'
        return data

    # socket发送字节流
    def BytesSend(self,client_socket,data):
        try:
            client_socket.send(data)
        except ConnectionResetError:
            return '连接断开'

    # 准备好接收(分片数校验)
    def GetReady(self,client_socket,client_name):
        frame = self.__frame
        if client_name in self.__sub_thread:
            frame = self.__sub_thread[client_name][0]
            
        print(client_name,'数据接受开始-------------------------')

        # 接受本次通信分片数
        data = self.BytesRecv(client_socket,256)
        if data == '连接断开':
            print(client_name,'数据接受结束，连接断开------------------------\n')
            return '连接断开' 

        frame_num = frame.DecodeFrameNum(client_name,data)
        if frame_num == -1:
            print(client_name,'数据接受结束，校验错误------------------------\n')
            return 'crc error'
            
        print(client_name,'本次接受分片数',frame_num)
         
        # 返回分片数应答
        frame.Reset()
        ack_data = '分片{}'.format(frame_num).encode('utf-8')
        frame.Code(ack_data)
        client_socket.send(ack_data)
        
        return frame_num

    # 从服务器接受数据
    def DataRecv(self,client_socket,client_name):
        frame = self.__frame
        if client_name in self.__sub_thread:
            frame = self.__sub_thread[client_name][0]

        # 先准备好接受(接受分片数并返回应答)
        frame_num = self.GetReady(client_socket,client_name)
        if not type(frame_num) == int:
            return frame_num
 
        # 开始接受并整合所有数据
        i = 0
        data = b''
        while i < frame_num:
            # 限制每次收帧长，可以处理部分粘包，但是依然不能解决帧截断和截断后粘连的问题
            data_f = self.BytesRecv(client_socket,256)     
            data,n,errCnt = frame.Decode(client_name,data_f,data)
            if errCnt != 0:
                print(client_name,'数据接受结束，校验错误-------------------------\n')
                return 'crc error'
            i += n

        print(client_name,'数据接受结束，成功-------------------------\n')
        return data

    # 发送数据
    def DataSend(self,client_socket,client_name,data):
        frame = self.__frame
        if client_name in self.__sub_thread:
            frame = self.__sub_thread[client_name][0]

        # 发送本次通信分片数
        max_size = frame.GetLoadNum()           # 最大负载长字节
        n = math.ceil(len(data)/max_size)       # 本次通信片数
        frame.Reset()                           # 先清理帧，避免之前传输的影响
        n_data = frame.Code(n.to_bytes(length=1 , byteorder="big"))
        self.BytesSend(client_socket,n_data)

        # 确定客户端已经装备好接受
        ack_n = self.BytesRecv(client_socket,1024)
        if ack_n == '连接断开':
            return '连接断开'
        if ack_n != '分片{}'.format(n).encode('utf-8'):
            return '分片通信错误'

        # 发送所有分片
        frame.Reset()                           # 清理帧
        while len(data) > max_size:
            sub_data = data[0:max_size]
            data = data[max_size:]
            file_content = frame.Code(sub_data)     
            self.BytesSend(client_socket,file_content)   
        
        file_content = frame.Code(data)         # 最后一个分片 
        self.BytesSend(client_socket,file_content)       

        return '发送完成'

    # 利用基本收发方法封装的一些方法--------------------------------------------------------------
    # 发送绝对地址，从服务器接收文件和目录列表（主线程）
    def RefreshListdir(self,path):
        name = 'client'
        socket = self.__socket
        frame = self.__frame
        
        # 请求目录
        self.DataSend(socket,name,path.encode('utf-8'))
        time.sleep(0.05)
        
        # 接收目录列表
        list_str = self.DataRecv(socket,name)

        if list_str == "无访问权限".encode('utf-8'):
            print("client：无权访问此目录")
            return "无访问权限"
        if list_str == 'crc error':
            print("client：通信错误")
            return "通信错误"
        if list_str == '连接断开':
            print("client：连接断开")
            return "连接断开"


        # 接受到的目录列表分解为目录名、文件名、文件尺寸3个列表
        list_str = list_str.decode('utf-8').split('<>')
        list_floders = list_str[0]
        list_files = list_str[1]
        list_sizes= list_str[2]

        self.__dir_floder = list_floders.split('/')
        self.__dir_files = list_files.split('/')
        self.__dir_sizes = list_sizes.split('/')

        # 刷新文件树
        self.__TransPorter.GetFileUI().treeWidget.RefreshDirTree(   path,
                                                                    self.__dir_floder,
                                                                    self.__dir_files,
                                                                    self.__dir_sizes)
        # 刷新Ico面板
        self.__TransPorter.GetFileUI().icoWidget.RefreshIcoWidget(  path,
                                                                    self.__dir_floder,
                                                                    self.__dir_files )
        return '成功'

    def Download(self,client_socket,client_name,pabr):
        frame = self.__sub_thread[client_name][0]

        # 请求文件
        path = self.__TransPorter.GetFileUI().treeWidget.GetFile()
        self.DataSend(client_socket,client_name,path.encode('utf-8'))
        time.sleep(0.05)
        
        # 先准备好接受(接受分片数并返回应答)
        frame_num = self.GetReady(client_socket,client_name)    # 分片数
        if not type(frame_num) == int:
            return frame_num
        
        # 打开下载进度窗口
        file_name = path[path.rfind('/')+1:]                    # 文件名
        self.pbar_create_signal.emit(pabr,file_name,frame_num)

        # 接受文件数据
        errCnt = 0
        i = 0
        step = 1 if int(frame_num/100)==0 else int(frame_num/100)   
        with open(self.__save_dir+"\\[donwload]"+file_name,"wb") as f: 
            while i < frame_num:
                
                data_f = self.BytesRecv(client_socket,256)
                if data_f == '连接断开':
                    self.__client_is_working = False
                    self.__connetion_cnt -= 1
                    self.connect_cnt_signal.emit(self.__connetion_cnt)     
                    self.transfer_pbar_signal.emit(pabr,-2,0)     
                    client_socket.close()          
                    return

                data,n,err = frame.Decode(client_name,data_f)        
                errCnt += err
                f.write(data)
                i += n

                # 每收到1%刷新一次进度，避免信号发送过于频率
                if i % step == 0:
                    self.transfer_pbar_signal.emit(pabr,i/step,errCnt)
          
        self.transfer_pbar_signal.emit(pabr,100,errCnt)
        print(client_name,"错误数：",errCnt)

        # 文件传输连接关闭，连接数-1
        self.__connetion_cnt -= 1
        self.connect_cnt_signal.emit(self.__connetion_cnt)     
        self.transfer_pbar_signal.emit(pabr,-1,0)          
        
        # 关闭传输socket
        client_socket.close()


    def Upload(self,client_socket,client_name,pabr):     
        frame = self.__sub_thread[client_name][0]

        # 发送上传文件命令
        self.DataSend(client_socket,client_name,'upload'.encode('utf-8'))
        time.sleep(0.05)

        # 获取文件
        file_path = self.__TransPorter.GetFileUI().treeWidget.GetFile()
        print(client_name,"发送文件",file_path)
    
        # 发送文件名
        file_name = file_path[file_path.rfind('/')+1:]                    # 文件名
        self.DataSend(client_socket,client_name,file_name.encode('utf-8'))

        # 发送本次通信分片数
        size = os.stat(file_path).st_size 
        max_size = frame.GetLoadNum()
        frame_num = math.ceil(size/max_size)       # 本次通信片数
        frame.Reset()
        f_num_data = frame.Code(frame_num.to_bytes(length=8 , byteorder="big"))
        self.BytesSend(client_socket,f_num_data)

        # 确定客户端已经装备好接受
        ack_n = self.BytesRecv(client_socket,1024)
        if ack_n == '连接断开':
            return '连接断开'
        if ack_n != '分片{}'.format(frame_num).encode('utf-8'):
            return '分片通信错误'
        print(client_name,'ack:',ack_n.decode('utf-8'))
        print(client_name,"已准备好通信")
        
        # 打开上传进度窗口
        self.pbar_create_signal.emit(pabr,file_name,frame_num)
        
        # 发送文件数据
        step = 1 if int(frame_num/100)==0 else int(frame_num/100)   
        with open(file_path,"rb") as f:             #直接以二进制读入，传输时不用encode和decode了
            print(client_name,'开始发送文件')
            
            frame.Reset()
            for i in range(frame_num) :
                data = f.read(max_size)             # 最多读最大负载长字节
                file_content = frame.Code(data)     # 获取帧的字节流数据
                client_socket.send(file_content)
                
                if i % step == 0:                   # 每收到1%刷新一次进度，避免信号发送过于频率
                    self.transfer_pbar_signal.emit(pabr,i/step,0)

            print(client_name,'文件发送完毕')

        
        self.transfer_pbar_signal.emit(pabr,100,0)
        self.__connetion_cnt -= 1
        self.connect_cnt_signal.emit(self.__connetion_cnt)  # 更新状态栏
        self.transfer_pbar_signal.emit(pabr,-1,0)           # 关闭并销毁下载进度窗口   

        # 关闭传输socket
        client_socket.close()      

    # 获取服务器桌面
    def OpenDesktop(self):
        if self.__TransPorter.IsDownloadTask():
            self.RefreshListdir(self.__server_desktop)

    # 获取服务器C盘
    def OpenDiskC(self):
        if self.__TransPorter.IsDownloadTask():
            self.RefreshListdir(self.__server_disk_c)


    # socket连接相关的方法-------------------------------------------------------------------------------------
    # 创建一个新连接
    def AddConnection(self,proc,name,pabr=None):       
        # 创建一个socket连接
        new_socket = self.CreatSocket()
        if new_socket == None:
            return
        new_socket.setblocking(False)                    # 子线程是非阻塞模式的(需要循环判断监听线程退出)
        new_socket.settimeout(5)                         # 超时值设为5s                    

        # 创建一个连接子线程
        if pabr == None:    # 不关联下载进度页面，这是心跳线程
            connection_thread = MyThread(name,proc,[new_socket,name])
        else:               # 下载线程，关联下载进度页面
            connection_thread = MyThread(name,proc,[new_socket,name,pabr])

        # 子线程统一加入__sub_thread管理
        if not name in self.__sub_thread:
            self.__sub_thread[name] = [Frame(),connection_thread,new_socket]
        
        # 注册socket
        self.DataSend(new_socket,name,self.__ID.encode('utf-8')) 

        # 启动连接子线程
        connection_thread.setDaemon(True)   # 子线程配置为守护线程，主线程结束时强制结束
        connection_thread.start()           

    # 心跳检测线程(每3s发送一个心跳包)
    def Heart(self,heart_socket,heart_name):
        time.sleep(3)
        while self.__client_is_working: 
            time.sleep(3)
            res = self.DataSend(heart_socket,heart_name,('heart ' + self.__ID).encode('utf-8'))
            if res == '连接断开':
                self.transfer_pbar_signal.emit(0,-3,0)
                self.__last_connection = True   
                break

        heart_socket.close()

 
    # 新建一个连接到到服务器的socket
    def CreatSocket(self):
        # 连接server
        while self.__client_is_working: 
            connection_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)    
            connection_socket.setblocking(True)
            connection_socket.settimeout(0.1)    
            
            try:
                # connect不能在同一个socket上快速重复调用，但是加time.sleep报重复connect，用非阻塞检测不到连接，只能这样每次创建新的socket
                connection_socket.connect((self.__ip,self.__port))  

                self.__connetion_cnt += 1
                if self.__connetion_cnt == 1:           # 第一个连接是client主线程
                    print('client','socket连接成功')
                elif self.__connetion_cnt == 2:         # 第二个连接是client心跳
                    print('heart','socket连接成功')
                else:                                   # 其他连接是下载线程
                    print('download{}'.format(self.__connetion_cnt-2),'socket连接成功')
                connection_socket.settimeout(5)   
                self.connect_cnt_signal.emit(self.__connetion_cnt)             # 更新状态栏
                break
            
            except socket.timeout:
                connection_socket.close()

        if self.__client_is_working:
            return connection_socket
        return None

    # 主线程连接到服务器, 入口
    def Connect2Server(self):
        # 连接server
        self.__socket = self.CreatSocket()
        if self.__socket == None:
            return
        
        # 接收服务器桌面路径
        self.DataSend(self.__socket,'client','获取桌面'.encode('utf-8'))
        desktop_path = self.DataRecv(self.__socket,'client')

        # 注册新客户端
        self.DataSend(self.__socket,'client','login new client'.encode('utf-8'))    # 向服务器申请注册
        ID = self.DataRecv(self.__socket,'client')                                  # 接受服务器分配的ID

        if desktop_path == '连接断开' or desktop_path == 'crc error' or ID == '连接断开' or ID == 'crc error':
            self.__client_is_working = False
            return 
        else:
            self.__server_desktop = desktop_path.decode('utf-8').replace('\\','/')
            self.__ID = ID.decode('utf-8')
        print('client','注册了ID',self.__ID)

        # 启动心跳进程
        print('client','尝试连接心跳进程')
        self.AddConnection(self.Heart,"Heart")   
        print('client','连接进程结束')

        self.__last_connection = False


