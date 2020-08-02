from PyQt5 import QtCore, QtGui, QtWidgets
import sip
import os
from myTreeWidget import MyTreeWidget,ImageDict
from myIcoWidget import MyIcoWidget
from myThread import MyThread
from PyQt5.QtWidgets import *
from UI_progressbar import ProgressWidget


class Ui_FileWindow(object):
    # 构造函数，在这里拿到TransPorter类对象引用，从而可以通过TransPorter访问其他窗口ui
    def __init__(self,TransPorter):
        self.__TransPorter = TransPorter
        self.__IcoList = list()
        self.__cwd = os.getcwd()        # 当前程序文件位置
        self.transfer_widgets = dict()  # 管理所有正在进行的传输进度页面,元素构成 (索引:[ProgressWidget UI对象,传输进度窗口对象])

    def setupUi(self, FileWindow):
        FileWindow.setObjectName("FileWindow")
        FileWindow.resize(700, 420)
        FileWindow.setMaximumHeight(420)
        FileWindow.setMinimumHeight(420)
        FileWindow.move(self.__TransPorter.GetMainWindow().frameGeometry().x()+20,
                        self.__TransPorter.GetMainWindow().frameGeometry().y()+20)
        FileWindow.setWindowIcon(QtGui.QIcon('images/Network.ico'))

        self.centralwidget = QtWidgets.QWidget(FileWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
 
        # 左边上按钮
        self.gridLayout_select = QtWidgets.QGridLayout()
        self.gridLayout_select.setObjectName("gridLayout_select")
        
        self.pbt_diskC = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_diskC.setObjectName("pbt_diskC")
        self.gridLayout_select.addWidget(self.pbt_diskC, 1, 0, 1, 1)

        self.pbt_desktop = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_desktop.setObjectName("pbt_desktop")
        self.gridLayout_select.addWidget(self.pbt_desktop, 3, 0, 1, 1)

        self.pbt_lastPath = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_lastPath.setObjectName("pbt_lastPath")
        self.gridLayout_select.addWidget(self.pbt_lastPath, 1, 1, 1, 1)

        self.pbt_selectFloder = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_selectFloder.setObjectName("pbt_selectFloder")
        self.gridLayout_select.addWidget(self.pbt_selectFloder, 0, 0, 1, 2)

        self.pbt_selectFile = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_selectFile.setObjectName("pbt_selectFile")
        self.gridLayout_select.addWidget(self.pbt_selectFile, 3, 1, 1, 1)

        # 左下文件树面板
        self.treeWidget = MyTreeWidget(self.centralwidget,self)
        self.gridLayout_select.addWidget(self.treeWidget, 4, 0, 1, 2)
        self.gridLayout.addLayout(self.gridLayout_select, 0, 0, 8, 1)

        # 中间分割线
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridLayout.addWidget(self.line, 0, 1, 8, 1)

        # 右边ICO显示面板
        self.icoWidget = MyIcoWidget(self.centralwidget,self)
        self.gridLayout.addWidget(self.icoWidget, 0, 2, 8, 1)

        # 其他
        FileWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(FileWindow)
        self.statusbar.setObjectName("statusbar")
        FileWindow.setStatusBar(self.statusbar)

        self.retranslateUi(FileWindow)
        QtCore.QMetaObject.connectSlotsByName(FileWindow)

        # 自定义部分
        self.__window = FileWindow
        
        self.pbt_diskC.clicked.connect(self.treeWidget.OpenDiskC)
        self.pbt_desktop.clicked.connect(self.treeWidget.OpenDesktop)
        self.pbt_desktop.clicked.connect(self.__TransPorter.GetClient().OpenDesktop)
        self.pbt_diskC.clicked.connect(self.__TransPorter.GetClient().OpenDiskC)
        self.pbt_selectFile.clicked.connect(self.FileTransfer)
        
        #self.pbt_lastPath.clicked.connect()
        self.pbt_selectFloder.clicked.connect(self.GetFileDir)
        self.treeWidget.clicked.connect(self.treeWidget.NodeSelected)
        self.treeWidget.tree_refresh_signal.connect(self.IcoRefresh)
        self.icoWidget.ico_refresh_signal.connect(self.TreeRefresh)

        # 由于Qt的部件都是线程不安全的，必须在主线程刷新UI，所以进度条刷新放在这边，用信号通信
        self.__TransPorter.GetClient().transfer_pbar_signal.connect(self.RefreshTransferPbar)
        self.__TransPorter.GetClient().pbar_create_signal.connect(self.CreateTransferWidget)
        
    def retranslateUi(self, FileWindow):
        _translate = QtCore.QCoreApplication.translate
        FileWindow.setWindowTitle(_translate("FileWindow", "File widget"))
        self.pbt_lastPath.setEnabled(False)
        self.pbt_diskC.setText(_translate("FileWindow", "C盘"))
        self.pbt_desktop.setText(_translate("FileWindow", "桌面"))
        self.pbt_lastPath.setText(_translate("FileWindow", "待开发"))
        self.pbt_selectFloder.setText(_translate("FileWindow", "选择文件夹"))
        self.pbt_selectFile.setText(_translate("FileWindow", "确认文件"))
        
    
    # 槽函数 ---------------------------------------------------------------------------------------
    def GetFileDir(self):
        dir_choosed = QtWidgets.QFileDialog.getExistingDirectory(self.__window, "选取文件夹", self.__cwd) 

        if dir_choosed == "":
            print("\n取消选择")
            return

        print("\n你选择的文件夹为:" + dir_choosed)

        # 上传模式，选择上传位置目录
        if not self.__TransPorter.IsDownloadTask():
            self.treeWidget.SetRootPath(dir_choosed)  
            self.treeWidget.file_root.setDisabled(False)
            self.treeWidget.back_node.setDisabled(False)
            self.statusbar.showMessage(dir_choosed)
            self.treeWidget.RefreshDirTree(dir_choosed)
            self.icoWidget.RefreshIcoWidget(dir_choosed)
        # 下载模式，选择保存文件目录
        else:
            self.__TransPorter.GetClient().SetSaveDir(dir_choosed)

    # 槽函数：文件树刷新时，刷新Ico面板
    def IcoRefresh(self,path,floders=[],files=[]):
        self.icoWidget.RefreshIcoWidget(path,floders,files)

    # 槽函数：Ico面板刷新时，刷新文件树
    def TreeRefresh(self,path):
        if not self.treeWidget.RefreshDirTree(path):
            self.statusbar.showMessage("无访问权限")

    # 槽函数：启动文件传输任务，创建一个到服务器的新连接
    def FileTransfer(self):
        # 申请一个传输记录索引
        pbarIndex = 0 
        while pbarIndex in self.transfer_widgets:
            pbarIndex += 1
        
        # 设置传输线程的名字（方便调试），建立连接
        n = self.__TransPorter.GetClient().GetConnectionCnt()
        if self.__TransPorter.IsDownloadTask():
            name = 'download{}'.format(n-1)     # 在没有传输的时候，有UI和心跳两条个线程，n=2
            self.__TransPorter.GetClient().AddConnection(self.__TransPorter.GetClient().Download,name,pbarIndex)
        else:
            name = 'upload{}'.format(n-1)   
            self.__TransPorter.GetClient().AddConnection(self.__TransPorter.GetClient().Upload,name,pbarIndex)

    # 槽函数：创建一个传输窗口
    def CreateTransferWidget(self,index,name,frameNum):
        Pwindow = QMainWindow()
        PBar = ProgressWidget(self,index,Pwindow,name,frameNum,self.__TransPorter.IsDownloadTask())
        self.transfer_widgets[index] = [PBar,Pwindow]
        Pwindow.show()

    # 槽函数：刷新文件传输进度条（QProgressBar禁止在其他线程刷新）
    def RefreshTransferPbar(self,index,value,errCnt):
        if value == -1:     # 传输完毕
            self.transfer_widgets[index][0].ActivatePbtFinish()
        elif value == -2:   # 传输失败
            self.transfer_widgets[index][0].ActivatePbtFinish()
            self.transfer_widgets[index][0].pbt_finish.setText('文件传输失败')
            self.transfer_widgets[index][0].statusbar.showMessage("连接中断，文件传输失败")
            self.__TransPorter.GetOptionUI().Break()
            self.__TransPorter.GetFileWindow().close()
        elif value == -3:   # 连接断开
            self.__TransPorter.GetOptionUI().Break()
            self.__TransPorter.GetFileWindow().close()            
        else:               # 正在传输
            self.transfer_widgets[index][0].SetProgress(value)
            if self.__TransPorter.IsDownloadTask():
                self.transfer_widgets[index][0].statusbar.showMessage("错误帧数:{}".format(errCnt))

    # 销毁下载窗口
    def DestroyTransferWidget(self,index):
        self.transfer_widgets[index][1].close()
        del self.transfer_widgets[index]

    # 显示file widget
    def ShowWindow(self,modeChange):
        if modeChange or self.__TransPorter.GetClient().IsNotConnecting():
            self.treeWidget.ClearFileTree()
            self.treeWidget.back_node.setDisabled(True)
            self.treeWidget.file_root.setDisabled(True)
            self.treeWidget.file_root.setText(0,'Current dir')
            self.icoWidget.Clear()

        self.pbt_selectFile.setEnabled(False)
        if self.__TransPorter.IsDownloadTask():
            self.pbt_selectFloder.setText('选择保存路径')
        else:
            self.pbt_selectFloder.setText('选择上传文件位置')

        self.__window.show()

    def GetTransPorter(self):
        return self.__TransPorter