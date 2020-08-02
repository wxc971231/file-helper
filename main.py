import sys
from PyQt5.QtWidgets import QMainWindow,QApplication
from UI_main import Ui_MainWindow,MyMainWindow
from UI_option import Ui_OptionWindow
from UI_file import Ui_FileWindow
from net_server import Server
from net_client import Client

# 文件传输器类
class TransPorter:
    # 构造函数
    def __init__(self):
        self.__mainWindow = MyMainWindow(self)          # main窗口
        self.__main_ui = Ui_MainWindow(self)            # main窗口ui对象

        self.__optionWindow = QMainWindow()             # option窗口
        self.__option_ui = Ui_OptionWindow(self)        # option窗口ui对象

        self.__fileWindow = QMainWindow()               # file窗口
        self.__file_ui = Ui_FileWindow(self)            # file窗口ui

        self.__server = Server()                        # 服务器对象
        self.__client = Client(self)
        self.__mode = None                              # 工作模式（服务器True/客户端False）
        self.__working = False                          # 正在工作标志
        self.__download = False                         # 上传还是下载

        self.__main_ui.setupUi(self.__mainWindow)       # 在main窗口建立ui
        self.__option_ui.setupUi(self.__optionWindow)   # 在option窗口建立ui
        self.__file_ui.setupUi(self.__fileWindow)       # 在file窗口建立ui

    # 启动传输器
    def Activate(self):
        self.__mainWindow.show() 

    # 作为服务器运行
    def RunAsServer(self,boolean):
        self.__mode = boolean
    
    # 获取工作模式
    def IsServer(self):
        return self.__mode

    # 设置工作状态
    def SetWroking(self,boolean):
        self.__working = boolean

    # 在工作吗
    def IsWorking(self):
        return self.__working

    # 设置任务状态
    def SetDownloadTask(self,boolean):
        self.__download = boolean

    # 是下载文件吗
    def IsDownloadTask(self):
        return self.__download

    # 获取option窗口UI对象
    def GetOptionUI(self):
        return self.__option_ui

    # 获取file窗口UI对象
    def GetFileUI(self):
        return self.__file_ui

    # 获取Mian窗口UI对象
    def GetMainUI(self):
        return self.__main_ui

    # 获取Mian窗口对象
    def GetMainWindow(self):
        return self.__mainWindow
    
    # 获取file窗口对象
    def GetFileWindow(self):
        return self.__fileWindow

    # 获取option窗口对象
    def GetOptionWindow(self):
        return self.__optionWindow

    # 获取服务器对象
    def GetServer(self):
        return self.__server
    
    # 获取客户端对象
    def GetClient(self):
        return self.__client

if __name__ == '__main__':

    app = QApplication(sys.argv)    # 创建应用程序对象
    postman = TransPorter()
    postman.Activate()              # 显示主窗口
    sys.exit(app.exec_())       