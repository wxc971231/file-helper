from PyQt5 import QtCore, QtGui, QtWidgets

# 文件传输UI
class ProgressWidget(QtCore.QObject):
    PbarClosed = QtCore.pyqtSignal()
    def __init__(self,fileUI,index,widget,fileName,frameNum,isDownload):
        super().__init__()
        self.fileUI = fileUI        # 文件选择窗口UI
        self.widget = widget        # 文件传输窗口,承载本UI
        self.index = index          # 文件传输窗口的索引
        self.fileName = fileName    # 传输文件名 
        self.frameNum = frameNum    # 传输文件分片数
        self.SetupUI(isDownload)
        

    def SetupUI(self,isDownload):
        self.widget.setObjectName("Downloading")
        self.widget.resize(318, 70)
        self.widget.setWindowIcon(QtGui.QIcon('images/Network.ico'))
        
        self.centralwidget = QtWidgets.QWidget(self.widget)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.label_name = QtWidgets.QLabel(self.centralwidget)
        self.label_name.setObjectName("label_name")
        self.gridLayout.addWidget(self.label_name, 1, 0, 1, 1)

        self.pbt_finish = QtWidgets.QPushButton(self.centralwidget)
        self.pbt_finish.setEnabled(False)
        self.pbt_finish.setObjectName("pbt_finish")
        self.gridLayout.addWidget(self.pbt_finish, 4, 0, 1, 3)
        self.label_name_ = QtWidgets.QLabel(self.centralwidget)
        self.label_name_.setObjectName("label_name_")
        self.gridLayout.addWidget(self.label_name_, 1, 1, 1, 2)
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout.addWidget(self.progressBar, 0, 0, 1, 3)
        self.label_frame = QtWidgets.QLabel(self.centralwidget)
        self.label_frame.setObjectName("label_frame")
        self.gridLayout.addWidget(self.label_frame, 2, 0, 1, 1)
        self.label_frame_ = QtWidgets.QLabel(self.centralwidget)
        self.label_frame_.setObjectName("label_frame_")
        self.gridLayout.addWidget(self.label_frame_, 2, 1, 1, 2)
        self.widget.setCentralWidget(self.centralwidget)
        
        self.statusbar = QtWidgets.QStatusBar(self.widget)
        self.statusbar.setObjectName("statusbar")
        self.widget.setStatusBar(self.statusbar)

        self.RetranslateUi(self.widget)
        QtCore.QMetaObject.connectSlotsByName(self.widget)
        self.SetTextInfo(isDownload)

        self.progressBar.setValue(0)
        self.label_name_.setText(self.fileName)
        self.label_frame_.setText(str(self.frameNum))

        self.pbt_finish.clicked.connect(self.DestroyWidget)

    def RetranslateUi(self, Mainwidget):
        _translate = QtCore.QCoreApplication.translate
        Mainwidget.setWindowTitle(_translate("downloading", "Downloading"))
        self.label_name.setText(_translate("downloading", "文件名："))
        self.label_frame_.setText(_translate("downloading", "TextLabel"))
        self.pbt_finish.setText(_translate("downloading", "完成"))
        self.label_name_.setText(_translate("downloading", "TextLabel"))
        self.label_frame.setText(_translate("downloading", "分片数："))
        
    # 销毁下载进度窗口
    def DestroyWidget(self):
        self.fileUI.DestroyTransferWidget(self.index)

    # 使能finish按钮
    def ActivatePbtFinish(self):
        self.pbt_finish.setEnabled(True)

    # 设置进度
    def SetProgress(self,value):
        self.progressBar.setValue(value)

    def SetTextInfo(self,isDownload):
        if isDownload:
            self.widget.setWindowTitle('Downloading')
            self.pbt_finish.setText('下载完成')
        else:
            self.widget.setWindowTitle('Uploading')
            self.pbt_finish.setText('上传完成')            


