import math
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QWidget,
                QPushButton, QComboBox, QTableView, QSizePolicy, QLabel, QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from iOSWeChatBackupTools import *
from iOSWeChatBackupReader import *
from weChatModel import *
from wxMediaViewerQT import *
from wxMessageWidgetQT import *

class WechatMessageViewer(QDialog):
    def __init__(self, parent, reader, user, session):
        QDialog.__init__(self, parent)
        self.reader = reader
        self.user = user
        self.session = session
        self.countPerPage = 20
        self.currentPage = 1
        self.__silkPlayer = SilkPlayer()
        self.__preLoadSessionMembers()
        self.__createView()

    def __preLoadSessionMembers(self):
        if self.session.isChatRoom:
            self.session.Members = self.reader.loadChatRoomMembers(self.user, self.session)
            if self.user.UserID not in self.session.Members:
                self.session.Members[self.user.UserID] = self.user

    def __createView(self):
        hbox1 = QHBoxLayout()
        self.messageViewModel = QStandardItemModel(0, 3)
        self.messageViewModel.setHorizontalHeaderLabels(["头像", "昵称", "消息内容", "消息时间"])

        self.messagesView = QTableView()
        self.messagesView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.messagesView.setModel(self.messageViewModel)
        self.messagesView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # 所有列自动拉伸
        self.messagesView.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # 禁止选择
        self.messagesView.setEditTriggers(QTableView.EditTrigger.NoEditTriggers) # 禁止编辑
        self.messagesView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.messagesView.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.messagesView.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.messagesView.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.messagesView.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        #self.messagesView.horizontalHeader().setMinimumSectionSize(100)         # 设置最小列宽
        hbox1.addWidget(self.messagesView)

        hbox2 = QHBoxLayout()
        self.prevBtn = QPushButton("上一页")
        self.prevBtn.setEnabled(False)
        self.prevBtn.clicked.connect(self.clickPrevBtn)
        hbox2.addWidget(self.prevBtn)
        self.nextBtn = QPushButton("下一页")
        self.nextBtn.setEnabled(False)
        self.nextBtn.clicked.connect(self.clickNextBtn)
        hbox2.addWidget(self.nextBtn)
        hbox2.addWidget(QLabel("当前页"))
        self.currentPageCB = QComboBox()
        self.totalPages = math.ceil(self.session.RecordCount / self.countPerPage)        # 20 default count per page
        self.currentPageCB.addItems([str(i) for i in range(1, self.totalPages + 1)])
        hbox2.addWidget(self.currentPageCB)
        hbox2.addStretch(1)
        hbox2.addWidget(QLabel("每页"))
        self.countPerPageCB = QComboBox()
        self.countPerPageCB.addItems(["20", "30", "50"])
        hbox2.addWidget(self.countPerPageCB)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        self.setLayout(vbox)
        # 直接 self.setWindowFlags(Qt.WindowType.WindowMinMaxButtonsHint) Dialog不会显示
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumSize(640, 480)
        self.setWindowTitle("与{}的聊天记录".format(self.session.DisplayName))

        self.__reloadMessagesFromDB(self.currentPage, self.countPerPage)  # initial load
        self.currentPageCB.currentTextChanged.connect(self.switchPageInComboBox)
        self.countPerPageCB.currentTextChanged.connect(self.switchCountPerPageInComboBox)

    def switchPageInComboBox(self):
        if self.currentPageCB.currentText() == "":
            return

        self.currentPage = int(self.currentPageCB.currentText())
        self.__reloadMessagesFromDB(self.currentPage, self.countPerPage)

    def switchCountPerPageInComboBox(self):
        if self.countPerPageCB.currentText() == "":
            return

        self.countPerPage = int(self.countPerPageCB.currentText())
        self.totalPages = math.ceil(self.session.RecordCount / self.countPerPage)
        self.currentPageCB.clear()
        self.currentPageCB.addItems([str(i) for i in range(1, self.totalPages + 1)])
    
    def __reloadMessagesFromDB(self, currentPage, countPerPage):
        self.messageViewModel.removeRows(0, self.messageViewModel.rowCount())
        msgRecords = self.reader.loadMessagesByPage(self.session.DBPath, "Chat_{}".format(self.session.UserID), currentPage, countPerPage)
        self.__parseMsgRecords(msgRecords)
        self.__adjustButtons(currentPage, countPerPage)
        self.messagesView.resizeRowsToContents()

    def widgetLinkActivated(self, href):
        clickedMsg = self.messages[int(href)]
        if clickedMsg["type"] == "audio":
            self.__silkPlayer.playBG(clickedMsg["src"])
        else:
            wechatMediaViewer = WechatMediaViewer(self, clickedMsg)
            if wechatMediaViewer.exec_():
                pass
            wechatMediaViewer.destroy()

    # CreateTime,Message,Des,Type,MesLocalID
    # Des = 0: send by me, other: send by other
    def __parseMsgRecords(self, msgRecords):
        self.messages = []
        for i, msgRecord in enumerate(msgRecords):
            parsedMsg = parseMessage(self.user, self.session, self.reader, msgRecord[2], MessageType(msgRecord[3]), msgRecord[1], msgRecord[4])

            self.messageViewModel.appendRow([QStandardItem(""), QStandardItem(parsedMsg.Sender.DisplayName), QStandardItem(""), QStandardItem(formatDatetime(msgRecord[0]))])
            self.messagesView.setIndexWidget(self.messageViewModel.index(i, 2), parsedMsg.createWidget())
            # 头像
            if parsedMsg.Sender.UserID != "":
                self.messagesView.setIndexWidget(self.messageViewModel.index(i, 0), WeChatWidget.createHeadImgWidget(parsedMsg.Sender))

            self.messages.append(parsedMsg)
    
    def __adjustButtons(self, currentPage, countPerPage):
        if self.totalPages == 1:
            self.prevBtn.setEnabled(False)
            self.nextBtn.setEnabled(False)
        elif currentPage == 1:
            self.prevBtn.setEnabled(False)
            self.nextBtn.setEnabled(True)
        elif currentPage == self.totalPages:
            self.prevBtn.setEnabled(True)
            self.nextBtn.setEnabled(False)
        else:
            self.prevBtn.setEnabled(True)
            self.nextBtn.setEnabled(True)
    
    def clickPrevBtn(self):
        self.currentPageCB.setCurrentText(str(self.currentPage - 1))
    
    def clickNextBtn(self):
        self.currentPageCB.setCurrentText(str(self.currentPage + 1))
    
    def resizeEvent(self, e):
        self.messagesView.resizeRowsToContents()
        super().resizeEvent(e)