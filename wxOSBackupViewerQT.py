import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                QPushButton, QComboBox, QWidget, QTableView, QSizePolicy, QFileDialog, QHeaderView, QAbstractItemView,
                QMessageBox)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from wxMessageViewerQT import *
from iOSWeChatBackupTools import *
from iOSWeChatBackupReader import *
from weChatModel import *
from wxMessageWidgetQT import *

class IOSWechatBackupViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.__createView()

    def __createView(self):
        hbox1 = QHBoxLayout()
        hbox1.addWidget(QLabel("用户列表"))
        self.usersViewCB = QComboBox()
        self.usersViewCB.currentTextChanged.connect(self.switchUserInComboBox)
        hbox1.addWidget(self.usersViewCB, 1)
        self.selectBackupFolderBtn = QPushButton("选择备份文件夹")
        self.selectBackupFolderBtn.clicked.connect(self.showSelectBackupFolderDialog)
        hbox1.addWidget(self.selectBackupFolderBtn)
        hbox1.addStretch(2)

        hbox2 = QHBoxLayout()
        self.sessionViewModel = QStandardItemModel(0, 6)
        self.sessionViewModel.setHorizontalHeaderLabels(["微信ID", "头像", "昵称", "别名", "总消息数", "开始时间", "结束时间"])

        self.sessionsView = QTableView()
        self.sessionsView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.sessionsView.setModel(self.sessionViewModel)
        self.sessionsView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # 所有列自动拉伸
        self.sessionsView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # 单选
        self.sessionsView.setEditTriggers(QTableView.EditTrigger.NoEditTriggers) # 禁止编辑
        self.sessionsView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # 整行选中
        self.sessionsView.verticalHeader().setDefaultSectionSize(60)
        self.sessionsView.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sessionsView.doubleClicked.connect(self.doubleClickSession)
        hbox2.addWidget(self.sessionsView)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        mainWidget = QWidget()
        mainWidget.setLayout(vbox)
        self.statusBar()
        self.setCentralWidget(mainWidget)
        self.setWindowTitle("微信聊天记录查看 - iOS备份文件")
        self.setMinimumSize(640, 480)
        self.show()
    
    def setOperationalWidgetEnabled(self, enabled):
        self.selectBackupFolderBtn.setEnabled(enabled)
        self.usersViewCB.setEnabled(enabled)

    def showSelectBackupFolderDialog(self):
        backupFolder = QFileDialog.getExistingDirectory(None, "选择备份文件夹：", os.getcwd(), QFileDialog.Option.ShowDirsOnly)
        if backupFolder and len(backupFolder) > 0:
            if os.path.exists(backupFolder + "/Manifest.db"):
                self.selectBackupFolderBtn.setEnabled(False)
                self.reader = IOSWeChatBackupReader(backupFolder)
                self.reader.loadManifestDB()
                self.loginUsers = self.reader.loadLoginUsers()
                self.addUsersToComboBox(self.loginUsers)
                self.selectBackupFolderBtn.setEnabled(True)
            else:
                QMessageBox.warning(self, "备份文件无效", "请选择正确的iTunes备份文件夹")

    def addUsersToComboBox(self, users):
        # 清除当前显示的用户和对话
        self.usersViewCB.clear()
        self.sessionViewModel.removeRows(0, self.sessionViewModel.rowCount())

        for userID in users:
            self.usersViewCB.addItem("{} ({})".format(users[userID].DisplayName, userID))

    def switchUserInComboBox(self):
        currentText = self.usersViewCB.currentText()

        if currentText != "":
            self.setOperationalWidgetEnabled(False)
            self.currentUser = self.loginUsers[currentText[currentText.index("(") + 1:currentText.index(")")]]
            
            self.sessions = self.reader.loadUserSessionList(self.currentUser)
            self.sessions.sort(key=lambda s:s.RecordCount, reverse=True)

            self.sessionViewModel.removeRows(0, self.sessionViewModel.rowCount())
            for i, session in enumerate(self.sessions):
                # ["微信ID", "头像", "昵称", "别名", "总消息数", "开始时间", "结束时间"]
                self.sessionViewModel.appendRow([QStandardItem(session.UserName), QStandardItem(""), QStandardItem(session.DisplayName), QStandardItem(session.AliasName),
                                                QStandardItem(str(session.RecordCount)), QStandardItem(session.BeginTime), QStandardItem(session.EndTime)])
                self.sessionsView.setIndexWidget(self.sessionViewModel.index(i, 1), WeChatWidget.createHeadImgWidget(session))

            self.setOperationalWidgetEnabled(True)
    
    def doubleClickSession(self, modelIndex):
        selSession = self.sessions[modelIndex.row()]
        wechatMessageViewer = WechatMessageViewer(self, self.reader, self.currentUser, selSession)
        if wechatMessageViewer.exec_():
            pass
        wechatMessageViewer.destroy()

app = QApplication(sys.argv)
viewer = IOSWechatBackupViewer()
sys.exit(app.exec())