import hashlib

def userNameToUserID(userName):
    return hashlib.md5(userName.encode("utf-8")).hexdigest()

class User(object):
    __userID = ""
    @property
    def UserID(self):
        return self.__userID
    @UserID.setter
    def UserID(self, userID):
        self.__userID = userID

    __userName = ""
    @property
    def UserName(self):
        return self.__userName
    @UserName.setter
    def UserName(self, userName):
        self.__userName = userName
        self.UserID = userNameToUserID(userName)

    __nickName = ""
    @property
    def NickName(self):
        return self.__nickName
    @NickName.setter
    def NickName(self, nickName):
        self.__nickName = nickName

    __aliasName = ""
    @property
    def AliasName(self):
        return self.__aliasName
    @AliasName.setter
    def AliasName(self, aliasName):
        self.__aliasName = aliasName

    @property
    def DisplayName(self):
        if self.__aliasName != "":
            return self.__aliasName
        elif self.__nickName != "":
            return self.__nickName
        elif self.__userName != "":
            return self.__userName
        return self.__userID

    __localHeadImg = ""
    @property
    def LocalHeadImg(self):
        return self.__localHeadImg
    @LocalHeadImg.setter
    def LocalHeadImg(self, localHeadImg):
        self.__localHeadImg = localHeadImg

    __headImgUrl = ""
    @property
    def HeadImgUrl(self):
        return self.__headImgUrl
    @HeadImgUrl.setter
    def HeadImgUrl(self, headImgUrl):
        self.__headImgUrl = headImgUrl

    __headImgUrlHD = ""
    @property
    def HeadImgUrlHD(self):
        return self.__headImgUrlHD
    @HeadImgUrlHD.setter
    def HeadImgUrlHD(self, headImgUrlHD):
        self.__headImgUrlHD = headImgUrlHD

    @property
    def isChatRoom(self):
        return self.UserName.endswith("@chatroom") or self.UserName.endswith("@im.chatroom")

    __msgTables = {}
    @property
    def MessageTables(self):
        return self.__msgTables
    @MessageTables.setter
    def MessageTables(self, msgTables):
        self.__msgTables = msgTables
    
    def toString(self):
        return self.__dict__

class Session(User):
    __beginTime = ""
    @property
    def BeginTime(self):
        return self.__beginTime
    @BeginTime.setter
    def BeginTime(self, beginTime):
        self.__beginTime = beginTime

    __endTime = ""
    @property
    def EndTime(self):
        return self.__endTime
    @EndTime.setter
    def EndTime(self, endTime):
        self.__endTime = endTime

    __recordCount = 0
    @property
    def RecordCount(self):
        return self.__recordCount
    @RecordCount.setter
    def RecordCount(self, recordCount):
        self.__recordCount = recordCount

    __dbPath = ""
    @property
    def DBPath(self):
        return self.__dbPath
    @DBPath.setter
    def DBPath(self, dbPath):
        self.__dbPath = dbPath
    
    __members = {}
    @property
    def Members(self):
        return self.__members
    @Members.setter
    def Members(self, members):
        self.__members = members


SystemSender = User()