from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIntValidator
from myThread import MyThread
import re

def IsIPV4(ip):
    compile_ip = re.compile('^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
    return compile_ip.match(ip)

class Ui_OptionWindow(object):
    # 构造函数，在这里拿到TransPorter类对象引用，从而可以通过TransPorter访问其他窗口ui
    def __init__(self,TransPorter):
        self.__TransPorter = TransPorter

    # 在传入参数OptionWindow上建立ui
    def setupUi(self, OptionWindow):
        # 自动生成部分
        OptionWindow.setObjectName("OptionWindow")
        OptionWindow.resize(300, 200)
        OptionWindow.move(self.__TransPorter.GetMainWindow().frameGeometry().x()+20,
                          self.__TransPorter.GetMainWindow().frameGeometry().y()+20)
        OptionWindow.setMaximumSize(QtCore.QSize(300, 200))
        self.centralwidget = QtWidgets.QWidget(OptionWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.serverButton = QtWidgets.QPushButton(self.centralwidget)
        self.serverButton.setObjectName("serverButton")
        self.gridLayout_2.addWidget(self.serverButton, 0, 0, 1, 1)
        self.clientButton = QtWidgets.QPushButton(self.centralwidget)
        self.clientButton.setObjectName("clientButton")
        self.gridLayout_2.addWidget(self.clientButton, 0, 1, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.portNum = QtWidgets.QLineEdit(self.centralwidget)
        self.portNum.setObjectName("portNum")
        self.gridLayout.addWidget(self.portNum, 0, 1, 1, 1)
        self.IPLabel = QtWidgets.QLabel(self.centralwidget)
        self.IPLabel.setObjectName("IPLabel")
        self.gridLayout.addWidget(self.IPLabel, 1, 0, 1, 1)
        self.portLabel = QtWidgets.QLabel(self.centralwidget)
        self.portLabel.setObjectName("portLabel")
        self.gridLayout.addWidget(self.portLabel, 0, 0, 1, 1)
        self.IPNum = QtWidgets.QLineEdit(self.centralwidget)
        self.IPNum.setObjectName("IPNum")
        self.gridLayout.addWidget(self.IPNum, 1, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 2)
        self.confirmButton = QtWidgets.QPushButton(self.centralwidget)
        self.confirmButton.setObjectName("confirmButton")
        self.gridLayout_2.addWidget(self.confirmButton, 2, 0, 1, 1)
        self.breakButton = QtWidgets.QPushButton(self.centralwidget)
        self.breakButton.setObjectName("breakButton")
        self.gridLayout_2.addWidget(self.breakButton, 2, 1, 1, 1)
        OptionWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(OptionWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 233, 26))
        self.menubar.setObjectName("menubar")
        OptionWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(OptionWindow)
        self.statusbar.setObjectName("statusbar")
        OptionWindow.setStatusBar(self.statusbar)

        self.retranslateUi(OptionWindow)
        QtCore.QMetaObject.connectSlotsByName(OptionWindow)

        # 手动修改部分
        self.__window = OptionWindow                                    # window指针
        OptionWindow.setWindowIcon(QtGui.QIcon('images/Network.ico'))   # 设置窗口图标
        
        regx = QtCore.QRegExp("^([0-9]|[1-9]\\d|[1-9]\\d{2}|[1-9]\\d{3}|[1-5]\\d{4}|6[0-4]\\d{3}|65[0-4]\\d{2}|655[0-2]\\d|6553[0-5])$");
        validator_Port = QtGui.QRegExpValidator(regx)
        self.portNum.setValidator(validator_Port)                       # 正则表达式限制prot输入

        regx = QtCore.QRegExp("\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b")        
        validator_IP = QtGui.QRegExpValidator(regx)
        self.IPNum.setValidator(validator_IP)                           # 正则表达式限制IP输入

        self.serverButton.clicked.connect(self.RunAsServer)               # 连接信号与槽
        self.clientButton.clicked.connect(self.RunAsClient)
        self.confirmButton.clicked.connect(self.Confirm)
        self.breakButton.clicked.connect(self.Break)

        self.__TransPorter.GetServer().new_client_signal.connect(self.NewClient)    # 连接sever的new_client_signal信号
        self.__TransPorter.GetClient().connect_cnt_signal.connect(self.NewConnect)  # 连接client的new_connect_signal

    def retranslateUi(self, OptionWindow):
        _translate = QtCore.QCoreApplication.translate
        OptionWindow.setWindowTitle(_translate("OptionWindow", "option"))
        self.serverButton.setText(_translate("OptionWindow", "配置为server"))
        self.clientButton.setText(_translate("OptionWindow", "配置为client"))
        self.IPLabel.setText(_translate("OptionWindow", "ip"))
        self.portLabel.setText(_translate("OptionWindow", "port"))
        self.confirmButton.setText(_translate("OptionWindow", "启动连接"))
        self.breakButton.setText(_translate("OptionWindow", "断开连接"))

    # server槽
    def RunAsServer(self):
        self.portNum.setEnabled(True)
        self.IPNum.setEnabled(False)
        self.confirmButton.setEnabled(True)
        self.__TransPorter.RunAsServer(True)
        server = self.__TransPorter.GetServer() # 更新并显示本机ip
        server.SaveSelfIP()                        
        self.IPNum.setText(server.GetIP())  

        self.IPLabel.setText("本机ip")
        self.portLabel.setText("监听port")

    # client槽
    def RunAsClient(self):
        self.portNum.setEnabled(True)
        self.IPNum.setEnabled(True)
        self.confirmButton.setEnabled(True)
        self.__TransPorter.RunAsServer(False)
        self.IPLabel.setText("目标ip")
        self.portLabel.setText("目标port")
    
    # confirm槽
    def Confirm(self):    
        if self.portNum.text() == '':
            self.statusbar.showMessage("配置错误，port禁止为空")
            return
        if not IsIPV4(self.IPNum.text()):
            self.statusbar.showMessage("配置错误，非法的ip地址")
            return
            
        port = int(self.portNum.text())   
        ip = self.IPNum.text()

        if self.__TransPorter.IsServer():
            self.__port = port
            self.__TransPorter.GetMainUI().uploadButton.setEnabled(False)
            self.__TransPorter.GetMainUI().downloadButton.setEnabled(False)
            server = self.__TransPorter.GetServer() 
            server.ServerStart(port)        # 启动服务器（开始监听）
            self.statusbar.showMessage("正在监听port:{}，client连接：0".format(port))
            self.__TransPorter.GetMainUI().statusbar.showMessage("正在监听port:{}，client连接：0".format(port))
        else:
            self.__TransPorter.GetMainUI().uploadButton.setEnabled(True)
            self.__TransPorter.GetMainUI().downloadButton.setEnabled(True)
            client = self.__TransPorter.GetClient()
            client.SetDestServer(port,ip)   # 设置目标port和ip
            client.ClientStart()            # 启动客户端
            self.statusbar.showMessage("connecting server")
            self.__TransPorter.GetMainUI().statusbar.showMessage("connecting server")
            
            # 用一个子线程连接服务器，若连接成功，就创建心跳线程，然后结束
            connection_thread = MyThread('connecting',self.__TransPorter.GetClient().Connect2Server)
            connection_thread.setDaemon(True)   # 子线程配置为守护线程，主线程结束时强制结束
            connection_thread.start()                        

        self.__TransPorter.SetWroking(True) # 设置工作标志
        self.ShowWindow()                   # 刷新窗口UI
            
    # break槽
    def Break(self):
        if self.__TransPorter.IsServer():
            self.__TransPorter.GetServer().ServerShutDown()
        else:
            self.__TransPorter.GetClient().ClientShutDown()

        self.statusbar.showMessage("连接断开")
        self.__TransPorter.GetMainUI().statusbar.showMessage("连接断开")
        self.__TransPorter.GetMainUI().downloadButton.setEnabled(False)
        self.__TransPorter.GetMainUI().uploadButton.setEnabled(False)
        self.__TransPorter.SetWroking(False) 
        self.ShowWindow()            
    
    # server连接了新的client，更新状态栏
    def NewClient(self,cnt):
        if self.__TransPorter.IsWorking():  # 可能有点击break按钮后，NewClient信号才到的情况
            self.statusbar.showMessage("正在监听port:{}，client连接：{}".format(self.__port,cnt))
            self.__TransPorter.GetMainUI().statusbar.showMessage("正在监听port:{}，client连接：{}".format(self.__port,cnt))

    # client和server创建了新连接，更新状态栏
    def NewConnect(self,cnt):
        if cnt >= 2:                        # 没有文件传输时，有两个连接（UI和心跳）
            self.statusbar.showMessage("已连接，传输线程:{}".format(cnt-2))
            self.__TransPorter.GetMainUI().statusbar.showMessage("已连接，传输线程:{}".format(cnt-2))
        else:
            self.statusbar.showMessage("连接断开")
            self.__TransPorter.GetMainUI().statusbar.showMessage("连接断开")

    # 显示窗口
    def ShowWindow(self):
        if self.__TransPorter.IsWorking():  
            self.clientButton.setEnabled(False)
            self.serverButton.setEnabled(False)  
            self.IPNum.setEnabled(False)
            self.portNum.setEnabled(False)
            self.confirmButton.setEnabled(False)
            self.breakButton.setEnabled(True)
        else:
            self.clientButton.setEnabled(True)
            self.serverButton.setEnabled(True)
            self.IPNum.setEnabled(False)
            self.portNum.setEnabled(False)
            self.IPNum.setText("")
            self.portNum.setText("")
            self.confirmButton.setEnabled(True)
            self.breakButton.setEnabled(False)

        self.__window.show()
