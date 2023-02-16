from enum import Enum
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from weChatModel import *
from iOSWeChatBackupTools import *
from wxResourcesMgr import *

class MessageType(Enum):
    MT_Text = 1
    MT_Image = 3
    MT_Audio = 34
    MT_Video = 43
    MT_Emoticon = 47
    MT_AppMessage = 49
    MT_System = 10000
    MT_System_Recalled = 10002

class Message(object):
    def __init__(self, user, session, type):
        self.__user = user
        self.__session = session
        self.__type = type
        self.userRelativePath = "Documents/" + self.__user.UserID + "/"
        self.mediaRelativePath = "Documents/" + self.__user.UserID + "/{}/" + self.__session.UserID + "/"

    __type: MessageType
    @property
    def Type(self):
        return self.__type
    @Type.setter
    def Type(self, type):
        self.__type = type

    __user: User
    @property
    def User(self):
        return self.__User

    __session: Session
    @property
    def Session(self):
        return self.__session

    __sender: User
    @property
    def Sender(self):
        return self.__sender
    @Sender.setter
    def Sender(self, sender):
        self.__sender = sender
    
    __content = ""
    @property
    def Content(self):
        return self.__content
    @Content.setter
    def Content(self, content):
        self.__content = content

    def toString(self):
        return str(self.__dict__)

    def __addUnknownSenderToMembers(self, reader, senderID, senderName):
        friend = User()
        friends = reader.loadFriendsDetailsFromContact(self.__user, [senderName])
        if len(friends) == 1:
            friend = friends[0]
        else:
            print("cannot find in DB for User: {}".format(senderName))
            friend.UserName = senderName
        self.__session.Members[senderID] = friend
        return self.__session.Members[senderID]

    def getSenderFromSessionMembers(self, reader, senderName):
        senderID = userNameToUserID(senderName)
        if senderID not in self.__session.Members:
            self.__addUnknownSenderToMembers(reader, senderID, senderName)
        return self.__session.Members[senderID]

    def __parseSender(self, reader, des, message):
        if des == 0:
            return self.__user
        else:
            if self.__session.isChatRoom:
                if message.find(":\n") != -1:
                    senderName = message[:message.index(":\n")]
                    return self.getSenderFromSessionMembers(reader, senderName)
                return None
            else:
                return self.__session

    def __parseContent(self, des, message):
        if des == 0:
            return message
        else:
            if self.__session.isChatRoom:
                if message.find(":\n") != -1:
                    return message[message.index(":\n") + len(":\n"):]
        return message
    
    def parseSenderAndContent(self, reader, des, message):
        return self.__parseSender(reader, des, message), self.__parseContent(des, message)

    def parse(self, reader, des, msgType, message, resID):
        self.__sender, self.__content = self.parseSenderAndContent(reader, des, message)
        return self

    def createWidget(self):
        pass

class TextMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_Text)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)
        return self

    def createWidget(self):
        qlabel = QLabel(self.Content)
        qlabel.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        qlabel.setWordWrap(True)
        return qlabel

class ImageMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_Image)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)
        self.__src = reader.getRealPathByRelativePath(self.mediaRelativePath.format("Img") + str(resID) + ".pic")
        self.__thumb = reader.getRealPathByRelativePath(self.mediaRelativePath.format("Img") + str(resID) + ".pic_thum")
        return self

    def createWidget(self):
        imageLabel = QLabel("<a href='img'>[Image]</a>")
        imageLabel.setToolTip("<img src='{}' />".format(self.__thumb if self.__thumb else self.__src))
        imageLabel.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        imageLabel.linkActivated.connect(self.widgetLinkActivated)
        return imageLabel
    
    def widgetLinkActivated(self, href):
        openFileByBrowser(self.__src if self.__src else self.__thumb)

globalSilkPlayer = SilkPlayer()
class AudioMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_Audio)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)
        self.__src = reader.getRealPathByRelativePath(self.mediaRelativePath.format("Audio") + str(resID) + ".aud")
        self.__length = math.ceil(int(XmlParser(self.Content).getAttributeValueByPath("/msg/voicemsg", "voicelength"))/1000)
        return self

    def createWidget(self):
        audioLabel = QLabel("<a href='audio'>[Audio]</a>")
        audioLabel.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        audioLabel.linkActivated.connect(self.widgetLinkActivated)
        return audioLabel

    def widgetLinkActivated(self, href):
        globalSilkPlayer.playBG(self.__src)

class VideoMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_Video)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)

        xmlParser = XmlParser(self.Content)
        senderName = xmlParser.getAttributeValueByPath("/msg/videomsg", "fromusername")

        self.Sender = self.getSenderFromSessionMembers(reader, senderName)
        self.__src = reader.getRealPathByRelativePath(self.mediaRelativePath.format("Video") + str(resID) + ".mp4")
        self.__thumb = reader.getRealPathByRelativePath(self.mediaRelativePath.format("Video") + str(resID) + ".video_thum")
        self.__width = int(xmlParser.getAttributeValueByPath("/msg/videomsg", "cdnthumbwidth"))
        self.__height = int(xmlParser.getAttributeValueByPath("/msg/videomsg", "cdnthumbheight"))
        return self

    def createWidget(self):
        videoLabel = QLabel("<a href='video'>[Video] {}</a>".format("<span>（视频丢失）</span>" if (self.__src == None) else ""))
        videoLabel.setToolTip("<img src='{}' />".format(self.__thumb if self.__thumb else self.__src))
        videoLabel.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        videoLabel.linkActivated.connect(self.widgetLinkActivated)
        return videoLabel

    def widgetLinkActivated(self, href):
        openFileByBrowser(self.__src if self.__src else self.__thumb)

class EmoticonMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_Emoticon)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)

        xmlParser = XmlParser(self.Content)
        senderName = xmlParser.getAttributeValueByPath("/msg/emoji", "fromusername")

        self.Sender = self.getSenderFromSessionMembers(reader, senderName)
        md5 = xmlParser.getAttributeValueByPath("/msg/emoji", "md5")
        self.__src = xmlParser.getAttributeValueByPath("/msg/emoji", "cdnurl")
        self.__thumb = xmlParser.getAttributeValueByPath("/msg/emoji", "thumburl")

        self.__localSrc = WeChatResources().downloadEmoticon(self.__src, md5)
        return self

    def createWidget(self):
        imageLabel = QLabel("<a href='img'>[Emoticon]</a>")
        imageLabel.setToolTip("<img src='{}' />".format(self.__localSrc))
        imageLabel.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        imageLabel.linkActivated.connect(self.widgetLinkActivated)
        return imageLabel
    
    def widgetLinkActivated(self, href):
        openFileByBrowser(self.__localSrc)

class ApplicationMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_AppMessage)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)

        xmlParser = XmlParser(self.Content)
        senderName = xmlParser.getNodeValueByPath("/msg/fromusername")
        self.appMsgType = int(xmlParser.getNodeValueByPath("/msg/appmsg/type"))
        appID = xmlParser.getAttributeValueByPath("/msg/appmsg/type", "appid")
        if appID != "":
            appName = xmlParser.getNodeValueByPath("/msg/appinfo/appname")
            appIcon = reader.getRealPathByRelativePath(self.userRelativePath + "appicon{}.png".format(appID))

        self.Sender = self.getSenderFromSessionMembers(reader, senderName)

        return self

    def __createWidgetForDefault(self):
        xmlParser = XmlParser(self.Content)
        title = xmlParser.getNodeValueByPath("/msg/appmsg/title")
        thumburl = xmlParser.getNodeValueByPath("/msg/appmsg/thumburl")

        if title != None and title != "" and thumburl != None and thumburl != "":
            label = QLabel("<a href='{}'>[{}]</a>".format(thumburl, title))
        elif title != None and title != "":
            label = QLabel("<a href='app'>[{}]</a>".format(title))
        else:
            label = QLabel("<a href='app'>[Link]</a>")
        label.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        return label

    # 1: Text, 2: Image, 3: Audio, 4: Video, 5: Url, 6: Attach, 7: Open, 8: Emoji, 9: Voice_Remind, 10: Scan_Good
    # 13: Good, 15: Emotion, 16: Card_Ticket, 17: Realtime_Location, 19: Fwd_Msg, 50: Channel_Card
    # 51: Channels, 57: Refer, 2000: Transfers, 2001: Red_Envelopes: 100001: Reader_Type
    # other: unknown
    def createWidget(self):
        if self.appMsgType in [1, 8, 2001]:
            return self.__createWidgetForDefault()
        elif self.appMsgType in [33]:
            return self.__createWidgetForDefault()
        else:
            print("unsupport app type: {}".format(self.appMsgType))
            return QLabel(self.Content)

class WechatTemplate:
    def __init__(self, templateContent):
        self.__templateContent = templateContent
    
    def process(self, xmlNodes):
        for xmlNode in xmlNodes:
            linkName = xmlNode.xpath("@name")
            linkType = xmlNode.xpath("@linkType")
            linkHidden = xmlNode.xpath("@linkHidden")

            if linkHidden != "1":
                if linkType == "link_plain":
                    linkValue = xmlNode.xpath("/plain/text()")
                elif linkType == "link_profile":
                    linkValues = xmlNode.xpath("/memberlist/member/nickname/text()")
                    linkSep = xmlNode.xpath("/separator/text()")
                    linkValue = linkSep.join(linkValues)
                elif linkType == "link_admin_explain":
                    linkValue = xmlNode.xpath("/title/text()")
                elif linkType == "link_revoke_qrcode":
                    linkValue = xmlNode.xpath("/title/text()")
                elif linkType == "new_link_succeed_contact":
                    linkValue = xmlNode.xpath("/title/text()")
                else:
                    linkValue = xmlNode.xpath("/title/text()")
                self.__templateContent = self.__templateContent.replace("${}$".format(linkName), linkValue)
            else:
                self.__templateContent = self.__templateContent.replace("${}$".format(linkName), "")
        return self.__templateContent

class SystemMessage(Message):
    def __init__(self, user, session):
        super().__init__(user, session, MessageType.MT_System)

    def parse(self, reader, des, msgType, message, resID):
        super().parse(reader, des, msgType, message, resID)
        
        if self.Sender == None:
            self.Sender = SystemSender

        systemMessage = self.Content
        if systemMessage.startswith("<sysmsg"):
            xmlParser = XmlParser(systemMessage)
            sysMsgType = xmlParser.getAttributeValueByPath("/sysmsg", "type")
            if sysMsgType == "sysmsgtemplate":
                templateType = xmlParser.getAttributeValueByPath("/sysmsg/sysmsgtemplate/content_template", "type")
                if templateType.startswith("tmpl_type_profile") or templateType == "tmpl_type_admin_explain" or templateType == "new_tmpl_type_succeed_contact":
                    plainText = xmlParser.getNodeValueByPath("/sysmsg/sysmsgtemplate/content_template/plain")
                    if plainText != "":
                        templateContent = xmlParser.getNodeValueByPath("/sysmsg/sysmsgtemplate/content_template/template")
                        systemMessage = WechatTemplate(templateContent).process(xmlParser.getNodeByPath("/sysmsg/sysmsgtemplate/content_template/link_list/link"))
                        print(systemMessage, templateContent)
        else:
            # remove html tag
            c = removeHtml(systemMessage)

        self.__message = systemMessage

        return self

    def createWidget(self):
        label = QLabel(self.__message)
        label.setStyleSheet("QLabel{padding:4px;border-radius:4px}")
        return label

def parseMessage(user, session, reader, des, msgType, message, resID):
    if msgType == MessageType.MT_Text:
        return TextMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_Image:
        return ImageMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_Audio:
        return AudioMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_Video:
        return VideoMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_Emoticon:
        return EmoticonMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_AppMessage:
        return ApplicationMessage(user, session).parse(reader, des, msgType, message, resID)
    elif msgType == MessageType.MT_System or msgType == MessageType.MT_System_Recalled:
        return SystemMessage(user, session).parse(reader, des, msgType, message, resID)
    else:
        print("unsupport {}-{}".format(msgType, message))
    return TextMessage(user, session).parse(reader, des, msgType, message, resID)

class WeChatWidget:
    @staticmethod
    def createHeadImgWidget(user):
        return QLabel("<a><img src='{}' width=\"60\" height=\"60\" /></a>".format(WeChatResources().getDisplayHeadImg(user)))