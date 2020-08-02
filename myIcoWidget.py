'''
- 文件选择窗口右边的Ico面板类和方法 + Ico图标类和方法

- Ico面板类继承自QScrollArea；

- 关键方法：
    - MyIcoWidget::RefreshIcoWidget(self,path)  根据path刷新Ico面板
    - FileIco::ClickdIco(self)                  根据Ico图标类自身信息实现目录切换(向下一级) 

- 这里只有一种目录切换(ClickdIco),会向外层file widget ui发射信号，同步刷新file tree widget
'''
from PyQt5 import QtCore, QtGui, QtWidgets
import os
import sip
from myTreeWidget import ImageDict

# ICO图标类
class FileIco():
    def __init__(self,widget,layout,size,num,name,UI,SA):
        # 承载关系：UI -> SA -> widget -> layout -> ICO
        self.__widget = widget      # 承载ICO的widget
        self.__layout = layout      # 承载ICO的网格布局
        self.__size = size          # ICO尺寸 (fixed)
        self.__name = name          
        self.__op = QtWidgets.QGraphicsOpacityEffect()  #透明的设置
        self.__ID = num             # ICO编号
        self.__UI = UI              # 文件窗口整体UI
        self.__SA = SA              # 承载ICO的QScrollArea

        self.setupUI()

    # 建立UI
    def setupUI(self):
        self.__pbt = QtWidgets.QPushButton(self.__widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.__pbt.sizePolicy().hasHeightForWidth())
        self.__pbt.setSizePolicy(sizePolicy)
        self.__pbt.setMinimumSize(QtCore.QSize(self.__size, self.__size))
        self.__pbt.setMaximumSize(QtCore.QSize(self.__size, self.__size))
        self.__pbt.setSizeIncrement(QtCore.QSize(0, 0))
        self.__pbt.setObjectName(self.__name)
        self.__layout.addWidget(self.__pbt, 2*int((self.__ID-1)/3), (self.__ID-1)%3+2, 1, 1)
        self.__pbt.clicked.connect(self.ClickdIco)

        self.__label = QtWidgets.QLabel(self.__widget)
        self.__label.setObjectName(self.__name)
        self.__layout.addWidget(self.__label, 2*int((self.__ID-1)/3)+1,(self.__ID-1)%3+2, 1, 1) 
        self.__label.setText(self.__name)
    
    # ICO点击事件
    def ClickdIco(self):
        if not self.__UI.GetTransPorter().IsDownloadTask():     # 上传模式
            if os.path.isdir(self.__path):                      # 如果是文件夹
                self.__UI.pbt_selectFile.setEnabled(False) 
                try:
                    os.listdir(self.__path)                     # 判断访问权限
                    self.__UI.statusbar.showMessage(self.__path)    # 更新状态栏
                    self.__SA.ico_refresh_signal.emit(self.__path)  # 发射信号，更新treeWidget
                    self.__SA.RefreshIcoWidget(self.__path)         # 更新ICO面板(最后这俩顺序不能反)
                except PermissionError:
                    self.__UI.statusbar.showMessage("无访问权限")    # 更新状态栏
            else:
                self.__UI.pbt_selectFile.setEnabled(True) 
                self.__UI.treeWidget.SetFile(self.__path)
                self.__UI.statusbar.showMessage(self.__path)
        else:                                                                   # 下载模式
            if self.__UI.GetTransPorter().GetClient().IsDir(self.__name):       # 如果是文件夹
                self.__UI.pbt_selectFile.setEnabled(False)                      
                status = self.__UI.GetTransPorter().GetClient().RefreshListdir(self.__path)
                if status == '成功':  
                    self.__UI.statusbar.showMessage(self.__path)                # 更新状态栏
                    floders,files = self.__UI.treeWidget.GetDirsAndFiles()
                    self.__SA.RefreshIcoWidget(self.__path,floders,files)       # 更新ICO面板
                else:
                    self.__UI.statusbar.showMessage(status)
            else:
                self.__UI.pbt_selectFile.setEnabled(True) 
                self.__UI.treeWidget.SetFile(self.__path)
                self.__UI.statusbar.showMessage(self.__path)
                
    # 设置ICO的名字(文件名)
    def SetName(self,name):
        self.__name = name
        self.__label.setText(name.center(8,' '))    # 长度小于8，则中心对齐
        self.__label.setMaximumWidth(65)            # 总长度不超过65

    # 设置ICO的浏览和点击图图片
    def SetImage(self,disImg,hoverImg):     
        self.__disImg = disImg
        self.__hoverImg = hoverImg
        self.__pbt.setStyleSheet('QPushButton{border-image:url(' +disImg+ ');}'                 # 直接显示图
                                  'QPushButton:hover{border-image: url(' + hoverImg + ');}')    # 鼠标移上去时显示的
    # 设置当前ICO对应的文件路径
    def SetPath(self,path):
        self.__path = path.replace('\\','/')

    # 隐藏ICO
    def SetVisible(self,boolean):
        if boolean:
            self.__op.setOpacity(1) #完全不透明
            self.__label.setText(self.__name)
        else:
            self.__op.setOpacity(0) #完全透明
            self.__label.setText("")
        
        self.__pbt.setEnabled(boolean)
        self.__pbt.setGraphicsEffect(self.__op)

    def GetLayout(self):
        return self.__layout

    def GetButton(self):
        return self.__pbt

    def GetLabel(self):
        return self.__label

# ICO面板,继承自QScrollArea
class MyIcoWidget(QtWidgets.QScrollArea):
    ico_refresh_signal = QtCore.pyqtSignal(str)
    def __init__(self,widget,ui):
        super().__init__(widget)
        self.__IcoNum = 0           # 当前图标数量
        self.__VisibleIcoNum = 0    # 当前可见图标数量
        self.__IcoList = list()     # 管理ICO的列表
        self.__widget = widget      # 承载QScrollArea的widget
        self.__UI = ui              # 文件窗口UI
        self.file_root_path = ''
        self.setupUI()

    def setupUI(self):
        self.setWidgetResizable(True)
        self.setMaximumHeight(373)
        self.setMaximumWidth(320)
        self.setMinimumHeight(373)
        self.setMinimumWidth(320)
        self.setObjectName("scrollArea")

        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 227, 457))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_ICO = QtWidgets.QGridLayout(self.scrollAreaWidgetContents) # 放Ico的网格布局
        
        self.Init()

    # 初始化Ico面板
    def Init(self):
        # 放12个透明图标占位
        self.__IcoNum = 12
        for i in range(1,13):
            Ico = FileIco(self.scrollAreaWidgetContents,self.gridLayout_ICO,60,i,'new',self.__UI,self)
            Ico.SetVisible(False)
            self.__IcoList.append(Ico)

    # 添加一个Ico
    def AddIco(self,fname,ftype,fpath):        
        # 如果当前可见ICO数量小于12，显示一个不可见的就行了
        if self.__VisibleIcoNum < self.__IcoNum:
            Ico = self.__IcoList[self.__VisibleIcoNum]
            Ico.SetVisible(True)
            Ico.SetName(fname)
            Ico.SetImage(ImageDict[ftype],ImageDict[ftype+'_s'])
            Ico.SetPath(fpath)

        # 如果没有隐藏ICO了，新建一个
        else:
            self.__IcoNum += 1
            Ico = FileIco(self.scrollAreaWidgetContents,self.gridLayout_ICO,60,self.__IcoNum,fname,self.__UI,self)
            Ico.SetName(fname)
            Ico.SetImage(ImageDict[ftype],ImageDict[ftype+'_s'])
            Ico.SetPath(fpath)

            self.__IcoList.append(Ico)

        self.__VisibleIcoNum += 1

    # 显示所有Ico
    def ShowAllIco(self):
        for Ico in self.__IcoList:
            Ico.SetVisible(True)

    # 清除所有Ico
    def Clear(self):
        for Ico in self.__IcoList[:12]: # 前12个设为透明的
            Ico.SetVisible(False)
        
        for Ico in self.__IcoList[12:]: # 多于12个图标的删除
            self.gridLayout_ICO.removeWidget(Ico.GetButton())
            sip.delete(Ico.GetButton())
            self.gridLayout_ICO.removeWidget(Ico.GetLabel())
            sip.delete(Ico.GetLabel())

        del(self.__IcoList[12:])        # 列表也要截断
        self.__VisibleIcoNum = 0
        self.__IcoNum = 12

    # 刷新所有文件夹图标
    def RefreshFlodersIco(self,floders):
        if floders == ['']:
            return
        for f in floders:        
            if not self.__UI.GetTransPorter().IsDownloadTask():
                floder_path = os.path.join(self.file_root_path, f)         # 文件路径
            else:
                if self.file_root_path[-1] != '/':
                    floder_path = self.file_root_path + '/' + f
                else:
                    floder_path = self.file_root_path + f

            self.AddIco(f,'floder',floder_path)

    # 刷新所有文件图标
    def RefreshFilesIco(self,files):
        if files == ['']:
            return
        for f in files:    
            if not self.__UI.GetTransPorter().IsDownloadTask():
                file_path = os.path.join(self.file_root_path, f)           # 文件路径

            else:
                if self.file_root_path[-1] != '/':
                    file_path = self.file_root_path + '/' + f
                else:
                    file_path = self.file_root_path + f
            
            file_type = f[f.rfind('.')+1:]
            if file_type not in ImageDict:    
                file_type = 'unknown'
            file_name = f[:f.rfind('.')]        
            self.AddIco(file_name,file_type,file_path)

    # 刷新Ico面板
    def RefreshIcoWidget(self,path,floders=[],files=[]):
        self.file_root_path = path
        
        # 先把以前的Ico面板清空
        self.Clear() 
                               
        # 上传模式
        if not self.__UI.GetTransPorter().IsDownloadTask(): 
            try:
                files = os.listdir(path)    
            except PermissionError:
                print("此文件夹禁止访问")
                return

            floders = []                
            i = 0
            while i < len(files):
                file_path = os.path.join(path, files[i])
                if os.path.isdir(file_path):
                    floders.append(files[i])
                    del files[i]
                else:
                    i += 1

            self.RefreshFlodersIco(floders)
            self.RefreshFilesIco(files)

        # 下载模式
        else:                                               
            self.RefreshFlodersIco(floders)
            self.RefreshFilesIco(files)

