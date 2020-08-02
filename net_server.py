'''
说明：
    - 在option窗口启动server后，会创建监听scoket，运行在监听子线程上，此后每收到一个client连接请求，就单独开一个子线程处理和此client的通信
    - 主线程通过共享变量 __server_is_listening 和监听子线程 及 所有client子线程通信，以保证关闭server时可以同时结束所有子线程
    - 监听子线程和所有client子线程中的socket都是非阻塞模式，否则无法实现对__server_is_listening的轮询
    - 每一个连接拥有一个私有的socket，并且运行在一个独立的线程上

    - 每接入一个客户端，至少建立两条socket连接(主连接、心跳连接)
        - 主连接：  在client浏览server文件目录时发送文件和目录列表
        - 心跳连接：client不断发送心跳包，报告自己仍在连接状态，超时时间为10秒，超时后这个client的所有连接将被关闭
        - 下载连接：client端每发起一个下载请求，就建立一个下载socket连接
    
    - 连接过程：
        - client端开启一个连接子线程，和server建立第一条连接，申请一个ID。在client端保存ID和这条连通的socket后，连接子线程结束
          接下来client主线程会利用这条socket向服务器请求文件列表，用于刷新file窗口UI
        - 主线程连接成功后，client立即发起心跳连接，建立socket连接后先发来client ID，明确其所属关系
        - 此后，每当client端发起一个下载请求，就新建一条连接。同样要先发来client ID，明确其所属关系。在下载文件发送完毕后，client发来关闭命令，结束这个连接
        - client关闭或断开后，server端清除所有连接

    - 线程管理：
        - self.__sub_thread字典：这里有所有除了监听线程以外的子线程，主要用于通信
                                元素构成 (线程名:[Frame对象,thread对象,Lock对象,所属客户端ID])
        - self.__sub_thread_union字典：这里按client为单位划分元素，每个元素中存储此client的所有子线程名，方便连接断开时断开所有连接
                                       元素构成 (所属客户端ID:[主线程名,心跳线程名,文件线程名...])
        - self.__sub_thread_heart列表：这里存储所有心跳线程名，只对它们进行超时检测
        - self.__died_client列表：这里存储所有处于已检测到断开，但尚未断开所有连接的client的ID

'''

import socket
import threading
from myThread import MyThread
from PyQt5 import QtCore
from protocol import Frame
import winreg
import time
import os
import random
import math

# 获取桌面路径
def GetDesktopPath():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    return winreg.QueryValueEx(key, "Desktop")[0]

# 构造一个UDP包但不发送，从中获取本机IP
def CheckIp(): 
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    finally:
        s.close()
    return IP

class Server(QtCore.QObject):
    new_client_signal = QtCore.pyqtSignal(int)   #每连接一个client，就向ui发一个信号，更新状态栏

    # 构造函数
    def __init__(self):
        super().__init__()
        self.SaveSelfIP()                   # 提取缓存本地ip      
        self.__running_client_cnt = 0       # 当前连接的客户端数量
        self.__thread_cnt = 0               # 线程计数
        self.__sub_thread = dict()          # 每个client线程有一个Frame对象空间,用字典管理。元素构成 (线程名:[Frame对象,thread对象,Lock对象,所属客户端ID])
        self.__sub_thread_union = dict()    # 每一个客户端会和服务器建立多条连接（主连接用来更新UI、心跳连接用来检测断连、数据连接用来传输数据）
                                            # 用一个字典管理同一个client的所有连接。元素构成 (所属客户端ID:[心跳线程名,主线程名,文件线程名...])    
        self.__sub_thread_heart = []        # 所有心跳线程集中到这。
        self.__died_client = []             # 断开的客户端ID暂存在这里，当其所有相关线程关闭后清除此项

    # 缓存本机ip地址 (构造一个UDP包但不发送 ，从中提取)
    def SaveSelfIP(self): 
        self.__ip = CheckIp()
    
    # 获取本机IP
    def GetIP(self):
        return self.__ip

    # 启动服务器（创建监听线程和套接字）
    def ServerStart(self,port):
        # 创建一个监听套接字
        print("server：创建了监听套接字")
        self.__server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) # 创建用于监听的socket    
        self.__server_socket.setblocking(False)                                 # 配置为非阻塞的socket
        self.__server_is_listening = False

        # 设置并绑定监听的端口
        print("server：设置并绑定port:{}".format(port))
        self.__server_socket.bind(("",port))
        self.__port = port

        # 启动监听线程
        self.__sub_thread.clear()           # 清空子线程记录
        self.__listenThread = MyThread("监听线程", self.Listen)
        self.__listenThread.setDaemon(True) #设置为守护线程，程序结束时强行结束监听
        self.__listenThread.start()

    # 关闭服务器（关闭所有子线程和套接字）
    def ServerShutDown(self):
        print("server：停止监听")   
        self.__server_is_listening = False  # 通过共享内存和子线程线程通信，关闭所有子线程和客户端线程
        self.__listenThread.join()          # 等待监听线程和所有客户端线程结束
        print("server：监听套接字关闭") 
        self.__server_socket.close()
        self.__running_client_cnt = 0

# 用于数据收发的基础方法---------------------------------------------------------------------------
    # socket接受
    def BytesRecv(self,client_socket,client_name,max_size):
        data = None
        timeout = 0
        ID = self.__sub_thread[client_name][2]              # 此线程所属客户端ID
        while data == None and self.__server_is_listening and not ID in self.__died_client:        
            try:
                data = client_socket.recv(max_size)
            except BlockingIOError:                         # 非阻塞socket，pass此异常以实现轮询
                pass
            except ConnectionAbortedError:
                if client_name in self.__sub_thread_heart:  # 客户端断开，可能出这个异常
                    self.HeartStop(client_name)  
                return '连接断开'
            except ConnectionResetError:                    # 客户端断开，可能出这个异常
                if client_name in self.__sub_thread_heart:
                    self.HeartStop(client_name)  
                return '连接断开'
            except socket.timeout:               
                if client_name in self.__sub_thread_heart:  # 只对心跳线程做超时判断
                    timeout += 5
                    print(client_name,'连接超时',timeout)
                    if timeout == 10:
                        self.HeartStop(client_name)
                        return '连接断开'
        if not self.__server_is_listening or data == b'':   # 客户端断开，data返回空串
            return '连接断开'
        return data

    # 线性安全的socket发送
    def BytesSend(self,client_socket,data):
        client_socket.send(data)

    # 准备好接收(获取分片数)
    def GetReady2Recv(self,client_socket,client_name):
        frame = self.__sub_thread[client_name][0]

        # 接受本次通信分片数
        data = self.BytesRecv(client_socket,client_name,256)
        if data == '连接断开':
            return '连接断开'  

        frame_num = frame.DecodeFrameNum(client_name,data)
        if frame_num == -1:
            return 'crc error'

        print(client_name,'本次接收分片数',frame_num)
         
        # 返回分片数应答
        frame.Reset()
        ack_data = '分片{}'.format(frame_num).encode('utf-8')
        frame.Code(ack_data)
        client_socket.send(ack_data)
        
        return frame_num

    def GetReady2Send(self,client_socket,client_name,size,isDownload):
        frame = self.__sub_thread[client_name][0]
                                 
        # 发送本次通信分片数
        max_size = frame.GetLoadNum()       # 最大负载长字节
        n = math.ceil(size/max_size)

        print(client_name,'本次发送分片数',n)
        frame.Reset()  
        if isDownload:
            n_data = frame.Code(n.to_bytes(length=8 , byteorder="big"))
        else:
            n_data = frame.Code(n.to_bytes(length=1 , byteorder="big"))

        self.BytesSend(client_socket,n_data)
        
        # 确定客户端已经装备好接受
        ack_n = self.BytesRecv(client_socket,client_name,1024).decode('utf-8')
        print(client_name,'ack:',ack_n)
        if ack_n == '连接断开':
            return '连接断开'
        if ack_n != '分片{}'.format(n):
            return '分片通信错误'
        print(client_name,"已准备好发送")
        return 'OK'

    # 接受数据
    def DataRecv(self,client_socket,client_name):
        frame = self.__sub_thread[client_name][0]

        # 先准备好接受(接受分片数)
        frame_num = self.GetReady2Recv(client_socket,client_name)
        if not type(frame_num) == int:
            return frame_num

        print(client_name,"准备接收分片",frame_num)
        
        # 开始接受并整合所有数据
        i = 0
        data = b''
        while i < frame_num:
            # 限制每次收帧长，可以解决部分粘包问题
            data_f = self.BytesRecv(client_socket,client_name,256)     
            data,n,errCnt = frame.Decode(client_name,data_f,data)
            if errCnt != 0:
                print(client_name,'数据接收结束，校验错误')
                return 'crc error'
            i += n

        #print(client_name,"有效数据 ",data)
        print(client_name,'数据接收结束，成功')
        return data


    # 发送数据
    def DataSend(self,client_socket,client_name,data):
        frame = self.__sub_thread[client_name][0]

        # 准备好发送
        res = self.GetReady2Send(client_socket,client_name,len(data),False)
        if res != 'OK':
            return res

        # 发送所有分片
        max_size = frame.GetLoadNum()       # 最大负载长字节
        frame.Reset()  
        while len(data) > max_size:
            sub_data = data[0:max_size]
            data = data[max_size:]
            file_content = frame.Code(sub_data)         # 拼数据帧
            self.BytesSend(client_socket,file_content)  # 发送数据

        # 发送最后一个分片
        file_content = frame.Code(data)             # 拼数据帧 
        self.BytesSend(client_socket,file_content)  # 发送数据

        print(client_name,"数据发送完成--------------------\n")
        return '发送完成'
            
# 利用基本收发方法封装的一些方法------------------------------------------------------------------
    # 发送path路径下的文件和目录信息
    def SendListDir(self,client_socket,client_name,path):
        print(client_name,"请求目录",path)
        try:
            items = os.listdir(path)    # 获取路径下所有文件名
        except PermissionError:
            print("无访问权限")
            self.DataSend(client_socket,client_name,'无访问权限'.encode('utf-8'))
            return

        # 分离文件和文件夹
        floders = []
        files = []
        sizes = []
        for item in items:
            file_path = os.path.join(path, item)
            if os.path.isdir(file_path):
                floders.append(item)
            else:
                size = str(round(os.stat(file_path).st_size/1024))
                files.append(item)
                sizes.append(size) 
        
        floder_str = '/'.join(floders)
        files_str = '/'.join(files)
        size_str = '/'.join(sizes)
        list_str = floder_str + '<>' + files_str + '<>' + size_str

        self.DataSend(client_socket,client_name,list_str.encode('utf-8'))

    def DownloadFile(self,client_socket,client_name,file_path):
        # 计算分片数        
        frame = self.__sub_thread[client_name][0]
        max_size = frame.GetLoadNum()       # 最大负载长字节
        size = os.stat(file_path).st_size 
        frame_num = math.ceil(size/max_size)
        
        # 准备好发送数据
        res = self.GetReady2Send(client_socket,client_name,size,True)
        if res != 'OK':
            return res
                
        # 发送文件数据
        print(client_name,'开始发送文件')
        with open(file_path,"rb") as f:             # 直接以二进制读入，传输时不用encode和decode了             
            frame.Reset()
            for i in range(frame_num) :
                data = f.read(max_size)             # 最多读最大负载长字节
                file_content = frame.Code(data)     # 获取帧的字节流数据
                print(client_name,len(file_content))
                client_socket.send(file_content)

        # 关闭传输socket
        print(client_name,'文件发送完毕')
        client_socket.close()

    def UploadFile(self,client_socket,client_name):
        frame = self.__sub_thread[client_name][0]
        frame.Reset()

        # 接收文件名
        file_name = self.DataRecv(client_socket,client_name)
        if not type(file_name) == bytes:
            return file_name
        file_name = file_name.decode('utf-8')
        print(client_name,'上传请求',file_name)

        # 接收并应答分片数
        frame_num = self.GetReady2Recv(client_socket,client_name)    # 分片数
        if not type(frame_num) == int:
            return frame_num

        # 接受文件数据
        i = 0
        errCnt = 0
        desktop_path = GetDesktopPath()
        with open(desktop_path+"\\[upload]"+file_name,"wb") as f: 
            while i < frame_num:
                # 限制每次收帧长，可以自动进行粘包处理
                data_f = self.BytesRecv(client_socket,client_name,256)     
                if data_f == '连接断开'.encode('utf-8'):
                    return

                data,n,err = frame.Decode(client_name,data_f)
                errCnt += err
                f.write(data)
                i += n

        # 关闭传输socket
        print(client_name,'错误帧数:',errCnt)
        client_socket.close()

# 接受数据后的处理--------------------------------------------------------------------------------
    # 客户端子线程（非阻塞socket）：接收客户端的各种请求
    def SubClientThread(self,client_socket,client_name):
        print(client_name + "：线程启动")

        # 给此线程一个Frame对象，用来构成帧
        if not client_name in self.__sub_thread:
            self.__sub_thread[client_name] = [Frame() , threading.currentThread(),''] #字典可自动添加

        # 轮询处理客户端的命令   
        while self.__server_is_listening:
            # 先检查此线程对应的客户端是不是已经断开连接,如果断开了,关闭连接
            thread_id = self.__sub_thread[client_name][2]
            if thread_id in self.__died_client:
                break

            data = self.DataRecv(client_socket,client_name)
            if type(data) == bytes:
                data = data.decode('utf-8')
            print(client_name,"接收数据",data,'-----------------------------\n')

            if data == '连接断开':
                break
            # client主线程发起注册
            elif data == 'login new client':
                self.Login(client_socket,client_name)
            # client子线程注册
            elif data in self.__sub_thread_union:
                self.__sub_thread[client_name][2] = data
                if not client_name in self.__sub_thread_union[data]:
                    self.__sub_thread_union[data].append(client_name)
            # 发送桌面
            elif data == "获取桌面":
                desktop_path = GetDesktopPath()
                if self.DataSend(client_socket,client_name,desktop_path.encode('utf-8')) == '连接断开':
                    self.StopSubThread(client_socket,client_name)
                    print(client_name,"通信结束")
                    break
            # client心跳
            elif data[:5] == 'heart':
                ID = data[6:]
                if not client_name in self.__sub_thread_union[ID]:
                    self.__sub_thread_union[ID].append(client_name)
                if not client_name in self.__sub_thread_heart:
                    self.__sub_thread_heart.append(client_name)
            # 上传
            elif data == 'upload':
                self.UploadFile(client_socket,client_name)
                break
            # 判断为目录则刷新
            elif os.path.isdir(data):
                self.SendListDir(client_socket,client_name,data)
            # 判断为文件则下载
            elif os.path.isfile(data): 
                self.DownloadFile(client_socket,client_name,data)
                break
            else:
                pass
            
        self.StopSubThread(client_socket,client_name)
        print(client_name,"通信结束")


# 线程控制相关--------------------------------------------------------------------------------
    # 结束子线程
    def StopSubThread(self,client_socket,client_name):
        # 从客户端线程集中清除此线程
        thread_id = self.__sub_thread[client_name][2]
        self.__sub_thread_union[thread_id].remove(client_name)

        # 如果这是断开的客户端的线程，且此断开客户端线程集已清空，把这个客户端ID移除
        if thread_id in self.__died_client and not self.__sub_thread_union[thread_id]:
            del self.__sub_thread_union[thread_id]
            self.__died_client.remove(thread_id)
        
        # 从全体线程集中清除此线程记录
        del self.__sub_thread[client_name]                     
           
        client_socket.close()
        self.__running_client_cnt -= 1
        self.new_client_signal.emit(self.__running_client_cnt)   # 向ui发信号，更新ui
    
    # 心跳线程断开后的处理
    def HeartStop(self,heart_name):
        self.__sub_thread_heart.remove(heart_name)  # 从心跳列表中移除此线程
        ID = self.__sub_thread[heart_name][2]       # 获取心跳超时的客户端ID
        self.__died_client.append(ID)               # 此心跳对应的客户端ID加入死亡client列表

    # 监听线程中启动监听socket，允许被动连接
    def Listen(self):
        print("server：开始监听")
        self.__server_socket.listen(128)
        self.__server_is_listening = True

        while self.__server_is_listening:
            try:
                client_socket,client_addr = self.__server_socket.accept()   # 设置setblocking(False)后, accept不再阻塞
                print("连接成功，客户端ip:{}，port:{}".format(client_addr[0],client_addr[1]))

                # 一旦连接成功，开一个子线程进行通信
                client_socket.setblocking(False)                    # 子线程是非阻塞模式的(需要循环判断监听线程退出)
                client_socket.settimeout(5)                         # 超时值设为5s                    
                self.__running_client_cnt += 1
                self.__thread_cnt += 1
                self.new_client_signal.emit(self.__running_client_cnt)      # 向ui发信号，更新ui
                client_name = "client{}".format(self.__thread_cnt)          # 创建子线程
                client_thread = MyThread(client_name, self.SubClientThread, [client_socket, client_name])
                client_thread.setDaemon(True)                       # 子线程配置为守护线程，主线程结束时强制结束
                client_thread.start()                               # 子线程启动

            except BlockingIOError:
                pass
                
    # 新连接注册
    def Login(self,client_socket,client_name):
        print('注册新client')
        # 生成一个唯一的key
        key = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz',10))
        while key in self.__sub_thread_union:
            key = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz',10))
        
        # 主线程加入字典   
        self.__sub_thread_union[key] = [client_name]                     
        self.__sub_thread[client_name][2] = key

        # 返回key
        self.DataSend(client_socket,client_name,key.encode('utf-8'))
        
