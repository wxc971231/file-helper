# 帧构成：学号(9byte) - 姓名(9byte) - 帧位置(4byte) - 数据(233byte) - 校验(1byte)
# 最大容量：2^32B = 4 GB

class Frame():
    def __init__(self):
        self.__datalist = []        # 字节流列表
        self.__loadMax = 256 - len('011610615魏晓晨'.encode('utf-8')) - 4 - 1 # 每一片的有效负载
        self.__pos = 0              # 本帧首字节位置(4byte)         
        self.__buf = b''            # 缓存buf,长256

        # frame head
        self.__datalist.append('011610615魏晓晨'.encode('utf-8'))

    # 返回有效负载
    def GetLoadNum(self):
        return self.__loadMax 

    # 填入校验字节
    def PutCRC(self):
        byte_cnt = 0
        byte_sum = 0
        
        for b in self.__datalist:
            for i in list(b):
                byte_sum += i
                byte_cnt += 1
                byte_sum %= 256

        self.__datalist.append(byte_sum.to_bytes(length=1 , byteorder="big"))

    # 编码一个帧，返回字节流
    def Code(self,data):
        # pos
        self.__datalist.append(self.__pos.to_bytes(length=4 , byteorder="big"))
        # data
        self.__datalist.append(data)
        self.__pos += len(data)
        # crc
        self.PutCRC()

        # get frame
        frame = '011610615魏晓晨'.encode('utf-8')
        for b in self.__datalist[1:]:
            frame += b

        # clear
        self.__datalist[1:] = []
        return frame

    # 重置帧（当一组数据发送完后需要重置）
    def Reset(self):
        self.__pos = 0
        self.__buf = b''
        self.__datalist[1:] = []

    # 分片数帧解码(这个一定是一帧传完，不需要考虑帧拼接，单独写一个解码)
    def DecodeFrameNum(self,connection_name,byte_flow):
        byte_crc = 0
        lst = list(byte_flow)
        for i in lst[0:-1]:
            byte_crc += i
            byte_crc %= 256
        
        if byte_crc == lst[-1]:
            print(connection_name,"收到分片数据，分片数校验成功")
        else:
            print(connection_name,"收到分片数据，分片数校验失败")
            return -1

        value = int.from_bytes(byte_flow[22:-1],'big')
        return value

    # 数据解码(长数据往往分了多个帧传输，解码byte_flow和data拼接后返回。由于网络的分片路由，需要手动处理各种帧粘包或截断情况)
    def Decode(self,connection_name,byte_flow,data = b''):
        if byte_flow == b'':
            if len(self.__buf) == 0:
                print(connection_name,'空错误')
                return data,1,1
            else:
                res,data = self.DecodeFrame(connection_name,self.__buf,data)
                if res == 'crc error':
                    return data,1,1
                else:
                    return data,1,0

        errCnt = 0
        n = 0
        while len(byte_flow) > 256:
            res,data = self.DecodeFrame(connection_name,byte_flow[:256],data)
            if res == 'crc error':
                errCnt += 1
            elif res == 'ok':
                n += 1
            byte_flow = byte_flow[256:]

        res,data = self.DecodeFrame(connection_name,byte_flow,data)
        if res == 'crc error':
            errCnt += 1
        elif res == 'ok':
            n += 1
        return data,n,errCnt

    # 解码一个数据帧，考虑各种粘包和截断情况
    def DecodeFrame(self,connection_name,byte_flow,data):   
        mode = 0
        # 帧首不是协议头
        if byte_flow[0:18] != '011610615魏晓晨'.encode('utf-8'):
            headPos = byte_flow.find('011610615魏晓晨'.encode('utf-8'))
            # 帧中部协议头没有出现，可能是帧的后半段
            if headPos == -1:
                # 拼接后长度不够最大帧长，连接到帧缓存后返回
                if len(byte_flow) + len(self.__buf) < 256:
                    print(connection_name,'重装',len(self.__buf),len(byte_flow))
                    self.__buf += byte_flow
                    return 'reload',data
                # 拼接后长度超过最大帧长，拼接出完整帧，清空帧缓存
                else:
                    print(connection_name,'进行拼接1',len(self.__buf),len(byte_flow))
                    byte_flow = self.__buf + byte_flow
                    self.__buf = b''
                    mode = 1
            # 帧中部出现协议头，前一半肯定是帧的后半段，拼接出完整帧；后一半可能是部分或完整帧，存入缓存       
            else:
                print(connection_name,'进行拼接2',len(self.__buf),len(byte_flow[:headPos]),len(byte_flow[headPos:]))
                temp = byte_flow[headPos:]
                byte_flow = self.__buf + byte_flow[:headPos]
                self.__buf = temp
                mode = 2
        # 是协议头
        else:
            # 帧中部出现协议头，前一半肯定完整帧；后一半可能是部分或完整帧，存入缓存
            headPos = byte_flow.find('011610615魏晓晨'.encode('utf-8'),18)
            if headPos != -1:
                self.__buf = byte_flow[headPos:]
                byte_flow = byte_flow[:headPos]

        pos = int.from_bytes(byte_flow[18:22], 'big')
        value = int.from_bytes(byte_flow[22:-1],'big')

        byte_crc = 0
        lst = list(byte_flow)
        for i in lst[0:-1]:
            byte_crc += i
            byte_crc %= 256
        
        # 效验成功
        if byte_crc == lst[-1]:
            data += byte_flow[22:-1]
            return 'ok',data
        # 效验失败
        else:
            # 如果长度不足最大帧长，可能是不完整，存入帧缓存
            if len(byte_flow) < 256:
                print(connection_name,'装载',len(self.__buf),len(byte_flow))
                self.__buf = byte_flow
                return 'load',data
            # 长度已到最大帧长，一定是传输出错
            else:
                print(connection_name,"收到分片数据，校验失败",mode,len(byte_flow),byte_crc,lst[-1])
                #print(byte_flow)
                return "crc error",data
            
    

        

