from PyQt5 import QtCore, QtGui, QtWidgets

# 对于主界面，重写其关闭事件，保证其关闭时连带关闭其他窗口
class MyMainWindow(QtWidgets.QMainWindow):
    def __init__(self,TransPorter):
        super().__init__()
        self.__TransPorter = TransPorter

    def closeEvent(self,event):
        self.__TransPorter.GetOptionWindow().close()
        self.__TransPorter.GetFileWindow().close()
        
class Ui_MainWindow(object):
    # 构造函数，在这里拿到TransPorter类对象引用，从而可以通过TransPorter访问其他窗口ui
    def __init__(self,TransPorter):
        self.__TransPorter = TransPorter

    #在传入参数MainWindow上建立ui
    def setupUi(self, MainWindow):
        #设置窗口
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(300, 200)
        MainWindow.move(700,400)
        MainWindow.setMaximumSize(QtCore.QSize(300, 200))
        MainWindow.setWindowIcon(QtGui.QIcon('images/Network.ico'))

        #在窗口上建立一个小窗口
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        #在小窗口建立一个网格布局
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")

        #在网格布局上放各种控件
        self.optionPic = QtWidgets.QLabel(self.centralwidget)
        self.optionPic.setObjectName("optionPic")
        self.optionPic.setStyleSheet('QLabel{border-image:url(images/option.jpg);}')
        self.optionPic.setFixedHeight(30)
        self.optionPic.setFixedWidth(30) 
        self.gridLayout.addWidget(self.optionPic, 0, 0, 1, 1)
    
        self.optionButton = QtWidgets.QPushButton(self.centralwidget)
        self.optionButton.setObjectName("optionButton")
        self.gridLayout.addWidget(self.optionButton, 0, 1, 1, 1)
        
        self.uploadPic = QtWidgets.QLabel(self.centralwidget)
        self.uploadPic.setObjectName("uploadPic")
        self.uploadPic.setStyleSheet('QLabel{border-image:url(images/upload.jpg);}')
        self.uploadPic.setFixedHeight(30)
        self.uploadPic.setFixedWidth(30)
        self.gridLayout.addWidget(self.uploadPic, 1, 0, 1, 1)

        self.uploadButton = QtWidgets.QPushButton(self.centralwidget)
        self.uploadButton.setObjectName("uploadButton")
        self.uploadButton.setEnabled(True)
        self.gridLayout.addWidget(self.uploadButton, 1, 1, 1, 1)

        self.downloadPic = QtWidgets.QLabel(self.centralwidget)
        self.downloadPic.setObjectName("downloadPic")
        self.downloadPic.setStyleSheet('QLabel{border-image:url(images/download.jpg);}')
        self.downloadPic.setFixedHeight(30)
        self.downloadPic.setFixedWidth(30)        
        self.gridLayout.addWidget(self.downloadPic, 2, 0, 1, 1)

        self.downloadButton = QtWidgets.QPushButton(self.centralwidget)
        self.downloadButton.setObjectName("downloadButton")
        self.downloadButton.setEnabled(True)
        self.gridLayout.addWidget(self.downloadButton, 2, 1, 1, 1)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 8)

        #设置小窗口为中心窗口
        MainWindow.setCentralWidget(self.centralwidget)

        #处理菜单栏和状态栏（这里其实没用到）
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 300, 26))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        self.statusbar.showMessage("连接未建立")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        #绑定信号和槽
        self.optionButton.clicked.connect(self.Option)
        self.downloadButton.clicked.connect(self.Download)
        self.uploadButton.clicked.connect(self.Upload)
        
        self.__TransPorter.GetMainUI().uploadButton.setEnabled(False)
        self.__TransPorter.GetMainUI().downloadButton.setEnabled(False)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "File Helper"))
        self.optionButton.setText(_translate("MainWindow", "连接配置"))
        self.uploadButton.setText(_translate("MainWindow", "上传"))
        self.downloadButton.setText(_translate("MainWindow", "下载"))

    #显示option窗口
    def Option(self):
        self.__TransPorter.GetOptionUI().ShowWindow()

    # 下载模式
    def Download(self):
        modeChange = False
        if not self.__TransPorter.IsDownloadTask():
            self.__TransPorter.SetDownloadTask(True)
            modeChange = True
        self.__TransPorter.GetFileUI().ShowWindow(modeChange)

    # 上传模式
    def Upload(self):
        modeChange = False
        if self.__TransPorter.IsDownloadTask():
            self.__TransPorter.SetDownloadTask(False)
            modeChange = True
        self.__TransPorter.GetFileUI().ShowWindow(modeChange)

    