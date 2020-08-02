'''
- 文件选择窗口左下角的treeWidget类和方法

- 关键方法：
    - RefreshDirTree(self,path):  根据path刷新文件树
    - NodeSelected(self):         文件树的点击事件的槽,可以进行目录切换(下一级或上一级)
    - OpenDesktop(self):          目录切换到本机桌面并刷新tree
    - OpenDiskC(self):            目录切换到C盘并刷新tree

- 所有的目录切换(NodeSelected中2种，OpenDesktop和OpenDiskC各一种)，都会向外层file widget ui发射信号，同步刷新ico面板
'''
from PyQt5 import QtCore, QtGui, QtWidgets
import os
import ctypes
from ctypes.wintypes import MAX_PATH
from net_server import GetDesktopPath

# 资源路径字典
ImageDict = dict([  
    ('doc_s'    ,   'images/file_ICO/doc_s.png'),
    ('doc'      ,   'images/file_ICO/doc.png'),
    ('docx_s'   ,   'images/file_ICO/docx_s.png'),
    ('docx'     ,   'images/file_ICO/docx.png'),
    ('floder_s' ,   'images/file_ICO/floder_s.png'),
    ('floder'   ,   'images/file_ICO/floder.png'),
    ('pdf_s'    ,   'images/file_ICO/pdf_s.png'),
    ('pdf'      ,   'images/file_ICO/pdf.png'),
    ('ppt_s'    ,   'images/file_ICO/ppt_s.png'),        
    ('ppt'      ,   'images/file_ICO/ppt.png'),
    ('pptx_s'   ,   'images/file_ICO/pptx_s.png'),
    ('pptx'     ,   'images/file_ICO/pptx.png'),
    ('txt_s'    ,   'images/file_ICO/txt_s.png'),
    ('txt'      ,   'images/file_ICO/txt.png'),
    ('xls_s'    ,   'images/file_ICO/xls_s.png'),
    ('xls'      ,   'images/file_ICO/xls.png'),
    ('xlsx_s'   ,   'images/file_ICO/xlsx_s.png'),
    ('xlsx'     ,   'images/file_ICO/xlsx.png'),
    ('zip_s'    ,   'images/file_ICO/zip_s.png'),
    ('zip'      ,   'images/file_ICO/zip.png'),
    ('dll_s'    ,   'images/file_ICO/dll_s.png'),
    ('dll'      ,   'images/file_ICO/dll.png'),
    ('exe_s'    ,   'images/file_ICO/exe_s.png'),
    ('exe'      ,   'images/file_ICO/exe.png'),
    ('png'      ,   'images/file_ICO/img.png'),
    ('png_s'    ,   'images/file_ICO/img_s.png'),
    ('jpg'      ,   'images/file_ICO/img.png'),
    ('jpg_s'    ,   'images/file_ICO/img_s.png'),
    ('ico'      ,   'images/file_ICO/img.png'),
    ('ico_s'    ,   'images/file_ICO/img_s.png'),
    ('rar'      ,   'images/file_ICO/zip.png'),
    ('rar_s'    ,   'images/file_ICO/zip_s.png'),
    ('mp4'      ,   'images/file_ICO/mp4.png'),
    ('mp4_s'    ,   'images/file_ICO/mp4_s.png'),
    ('md'       ,   'images/file_ICO/md.png'),
    ('md_s'     ,   'images/file_ICO/md_s.png'),

    ('unknown'  ,   'images/file_ICO/unknown.png'),
    ('unknown_s',   'images/file_ICO/unknown_s.png'),

    ('back'     ,   'images/file_ICO/back.png')
])

# 文件树类,继承自QTreeWidget
class MyTreeWidget(QtWidgets.QTreeWidget):
    tree_refresh_signal = QtCore.pyqtSignal(str,list,list)

    def __init__(self,widget,ui):
        super().__init__(widget)
        self.__widget = widget
        self.__UI = ui
        
        self.setObjectName("treeWidget")
        self.setColumnCount(2)
        self.setHeaderLabels(['file','size'])
        self.setColumnWidth(0,200)    # 第一列宽度200
        self.setColumnWidth(1,60)     # 第二列宽度300

        self.back_node = QtWidgets.QTreeWidgetItem(self)
        self.back_node.setText(0,'<Back>')
        self.back_node.setIcon(0,QtGui.QIcon(ImageDict['back']))
        self.back_node.setDisabled(True)

        self.file_root = QtWidgets.QTreeWidgetItem(self)
        self.file_root.setIcon(0,QtGui.QIcon(ImageDict['floder']))
        self.file_root.setText(0,'Current dir')
        self.file_root.setDisabled(True)

        self.file_root_dirs = []    # 当前根路径file_root_path下的目录列表
        self.file_root_files = []   # 当前根路径file_root_path下的文件列表
        
        self.transfer_file = ''     # 传输的文件路径
    
    # 清空file_root节点
    def ClearFileTree(self):
        for i in range(self.file_root.childCount()):
            self.file_root.removeChild(self.file_root.child(0))

    # 刷新文件树上的文件夹
    def RefreshFloder(self,floders):
        # 如果是刷新服务器列表，由于client中的拼接方法，空时列表为['']，需要特殊处理
        if floders == ['']:                                 
            return
        for f in floders:        
            floder = QtWidgets.QTreeWidgetItem(self.file_root)  
            floder.setText(0,f)
            floder.setText(1,'-    ')
            floder.setTextAlignment(1,QtCore.Qt.AlignRight)  # 第二列设为右对齐
            floder.setIcon(0,QtGui.QIcon(ImageDict['floder']))
            self.file_root.addChild(floder)
    
    # 刷新文件树上的文件
    def RefreshFiles(self,files,sizes):
        # 如果是刷新服务器列表，由于client中的拼接方法，空时列表为['']，需要特殊处理
        if files == [''] or sizes == ['']:
            return
        for f,s in zip(files,sizes):          
            child = QtWidgets.QTreeWidgetItem(self.file_root)             
            child.setText(0,f)                              # 第一列是文件名

            child.setText(1,s +' KB   ')
            child.setTextAlignment(1,QtCore.Qt.AlignRight)  # 第二列是文件大小，设为右对齐
            self.file_root.addChild(child)           

            pos = f.rfind('.')                              # 设置ico 
            file_type =  f[pos+1:]
            if file_type in ImageDict:    
                child.setIcon(0,QtGui.QIcon(ImageDict[file_type]))
            else:
                child.setIcon(0,QtGui.QIcon(ImageDict['unknown']))

    # 刷新file_root(如果是下载模式，用到后三个参数，client对象那边发起调用)
    def RefreshDirTree(self,path,floders = [],files = [],sizes = []):
        # 如果是本地访问，先遍历当前文件夹，分离文件夹和文件
        if not self.__UI.GetTransPorter().IsDownloadTask():
            try:
                items = os.listdir(path)    # 获取路径下所有文件名
            except PermissionError:
                print("无访问权限")
                return False

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

        self.file_root_dirs = floders
        self.file_root_files = files

        # 和Ico面板同步当前根目录
        self.file_root_path = path
        root = self.file_root

        # 先把以前的treeWidget清空
        self.ClearFileTree() 
                               
        # 设置根节点
        root_name = path[path.rfind('/')+1:] 
        if root_name == '' or root_name[-1] == ':': # 已到根目录 
            root_name = path[0:path.rfind('/')]
            self.back_node.setDisabled(True)
            self.setCurrentItem(self.file_root.child(1))
            print('根目录')
        else:                                       # 非根目录
            self.back_node.setDisabled(False)
        root.setText(0,root_name)

        # 刷新显示文件树
        self.RefreshFloder(floders)
        self.RefreshFiles(files,sizes) 

        #展开根节点
        self.file_root.setExpanded(True)

        return True


    # 在treeWidget中选择节点
    def NodeSelected(self):
        item = self.currentItem()

        # 非空值 且 不是当前file root
        if item and (item.parent() or item.text(0) == '<Back>') :
            node_path = self.file_root_path

            print("\n")
            print("now root:",node_path)
            print("now choose:",item.text(0))
            
            # 进入子目录
            if item.text(0) != '<Back>':
                if node_path[-1] != '/':
                    node_path = node_path + '/' + item.text(0)
                else:
                    node_path += item.text(0)
                print("sub dir：",node_path)

                # 上传模式，在本地查找文件列表
                if not self.__UI.GetTransPorter().IsDownloadTask():
                    if os.path.isdir(node_path):                        # 确认是目录
                        self.__UI.pbt_selectFile.setEnabled(False)      # 目录禁止上传
                        if not self.RefreshDirTree(node_path):          # 刷新文件树
                            self.__UI.statusbar.showMessage("无访问权限")
                        else:
                            self.file_root_path = node_path                 # 设定为新的根目录
                            self.__UI.statusbar.showMessage(node_path)      # 刷新状态栏
                            self.tree_refresh_signal.emit(node_path,[],[])  # 同步刷新Ico面板
                    else:
                        self.__UI.pbt_selectFile.setEnabled(True)       # 文件允许上传
                        self.transfer_file = node_path
                        self.__UI.statusbar.showMessage(node_path)
                
                # 下载模式，文件列表从服务器拿
                else:
                    if self.__UI.GetTransPorter().GetClient().IsDir(item.text(0)):    # 确认是目录
                        self.__UI.pbt_selectFile.setEnabled(False)          # 目录禁止上传
                        status = self.__UI.GetTransPorter().GetClient().RefreshListdir(node_path)
                        if status == '成功':                                # 刷新文件树
                            self.file_root_path = node_path                 # 设定为新的根目录
                            self.__UI.statusbar.showMessage(node_path)      # 刷新状态栏
                        else:
                            self.__UI.statusbar.showMessage(status)
                    else:
                        self.__UI.pbt_selectFile.setEnabled(True) 
                        self.transfer_file = node_path
                        self.__UI.statusbar.showMessage(node_path)

            # 回上层目录
            else:
                if self.back_node.isDisabled():
                    print("已到磁盘根目录")
                    return
                
                self.__UI.pbt_selectFile.setEnabled(False) 
                path = self.file_root_path
                path = path[0 : path.rfind('/')]
                self.file_root_path = path if path[-1] != ':' else path + '/'

                self.__UI.statusbar.showMessage(self.file_root_path)
                print("file tree：",self.file_root_path)
                
                if not self.__UI.GetTransPorter().IsDownloadTask():
                    self.RefreshDirTree(self.file_root_path)                    # 刷新文件树
                    self.tree_refresh_signal.emit(self.file_root_path,[],[])    # 发射信号同步刷新Ico面板
                else:
                    self.__UI.GetTransPorter().GetClient().RefreshListdir(self.file_root_path)  # 刷新文件树和Ico面板
                
                
    # 转到桌面
    def OpenDesktop(self):
        self.__UI.pbt_selectFile.setEnabled(False) 
        self.back_node.setDisabled(False)
        self.file_root.setDisabled(False)
        
        if not self.__UI.GetTransPorter().IsDownloadTask():
            path = GetDesktopPath()
        else: 
            path = self.__UI.GetTransPorter().GetClient().GetDesktopPath()
        path = path.replace('\\','/')

        self.file_root_path = path
        self.RefreshDirTree(path)
        self.__UI.statusbar.showMessage(self.file_root_path)
        
        # 本地Ico刷新在这里做（上传），如果是刷新服务器桌面（下载），在client获取服务器目录的函数里调用刷新
        if not self.__UI.GetTransPorter().IsDownloadTask():
            self.tree_refresh_signal.emit(path.replace('\\','/'),[],[])

    # 转到C盘
    def OpenDiskC(self):
        self.__UI.pbt_selectFile.setEnabled(False) 
        self.back_node.setDisabled(False)
        self.file_root.setDisabled(False)
        
        self.file_root_path = 'C:/'             # 刷新file dir
        self.RefreshDirTree('C:/')              # 刷新file tree
        self.__UI.statusbar.showMessage('C:/')  # 刷新状态栏

        # 本地Ico刷新在这里做（上传），如果是刷新服务器C盘（下载），在client获取C盘目录的函数里调用刷新
        if not self.__UI.GetTransPorter().IsDownloadTask():
            self.tree_refresh_signal.emit('C:/',[],[])
        
    # 设置file根目录
    def SetRootPath(self,path):
        self.file_root_path = path

    # 获取当前文件树根目录
    def GetRootPath(self):
        return self.file_root_path

    # 设置当前下载文件的路径
    def SetFile(self,file):
        self.transfer_file = file

    # 获取当前下载文件
    def GetFile(self):
        return self.transfer_file    

    # 获取当前file_root_path下的目录和文件
    def GetDirsAndFiles(self):
        return self.file_root_dirs,self.file_root_files
