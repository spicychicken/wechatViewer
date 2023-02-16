from lxml import etree
import mmkvpy
import threading

from iOSWeChatBackupTools import *
from weChatModel import *

class IOSWeChatBackupReader:
    def __init__(self, backupPath):
        self.__backupPath = backupPath

    def loadManifestDB(self):
        manifestDBReader = IOSBackupManifestDBReader(self.__backupPath)
        self.__records = manifestDBReader.loadRecordsByDomain("AppDomain-com.tencent.xin")
        self.__sharedRecords = manifestDBReader.loadRecordsByDomain("AppDomainGroup-group.com.tencent.xin")

    def getRealPathByRelativePath(self, relativePath):
        return self.__records.getRealPathByRelativePath(relativePath)

    def __loadUsersFromLoginInfo2(self, users):
        # 从LoginInfo2.dat加载Users, 假设只1个User, 多个User可通过1.2.3, 1.3.3, 1.4.3, 等, uid = md5(userName)
        usersFromLoginInfo2 = WeChatProtoReader().toJson(self.__records.getFileAsRawByRelativePath("Documents/LoginInfo2.dat"))

        for i in range(1, 10):
            if "1." + str(i) + ".1" in usersFromLoginInfo2:
                userName = usersFromLoginInfo2["1." + str(i) + ".1"].decode("utf-8")
                userID = userNameToUserID(userName)

                if userID not in users:
                    users[userID] = User()
                user = users[userID]

                user.UserID = userID
                user.UserName = userName
                user.NickName = usersFromLoginInfo2["1." + str(i) + ".3"].decode("utf8")
            else:
                break
        return users

    def __loadUsersFromMMDB(self, users):
        # 从Folder中加载Users (Documents/????????/DB/MM.sqlite)
        existUsersMsgDBRecords = self.__records.getRecordsByFilter(
            lambda record: record[1].startswith("Documents/") and record[1].endswith("/DB/MM.sqlite"))

        for userMsgDBRecord in existUsersMsgDBRecords:
            userID = userMsgDBRecord[1].split("/")[1]

            if userID not in users:
                users[userID] = User()
            user = users[userID]

            user.UserID = userID
        return users

    def __loadUserDetailsFromMMsetting(self, user):
        # user.UserName may not be exist
        # 从Documents/{uid}/mmsetting.archive 中加载User信息
        userSetting = self.__records.getFileAsPlistByRelativePath("Documents/" + user.UserID + "/mmsetting.archive", readType="biplist")
        if userSetting != None:
            userSettingWithValue = resolveBiplistUID(userSetting)

            user.UserName = userSettingWithValue["$objects"][1]["UsrName"]
            user.NickName = userSettingWithValue["$objects"][1]["NickName"]
            # 本机user没有AliasName, 如下值可能是修改后的UserName?
            # user.AliasName = userSettingWithValue["$objects"][1]["AliasName"]

            # new_dicsetting: NS.keys, NS.objects
            nsKeys = userSettingWithValue["$objects"][1]["new_dicsetting"]["NS.keys"]
            nsObjects = userSettingWithValue["$objects"][1]["new_dicsetting"]["NS.objects"]
            user.HeadImgUrl = nsObjects[nsKeys.index("headimgurl")]
            user.HeadImgUrlHD = nsObjects[nsKeys.index("headhdimgurl")]
        else:
            # 从Documents/MMappedKV/mmsetting.archive.{userName}加载
            existMMSettingDBRecords = self.__records.getRecordsByFilter(
                lambda record: record[1].startswith("Documents/MMappedKV/mmsetting.archive.") and record[1].endswith(".crc"))
            for record in existMMSettingDBRecords:
                userName = record[1].split(".")[2]
                if len(userName) > 0 and userNameToUserID(userName) == user.UserID:
                    mmkvFilePath = self.__records.getRealPathByRelativePath("Documents/MMappedKV/mmsetting.archive.{}".format(userName))
                    mmkvCrcFilePath = self.__records.getRealPathByRelativePath("Documents/MMappedKV/mmsetting.archive.{}.crc".format(userName))
                    userMMKVSetting = mmkvpy.parse(mmkvFilePath, mmkvCrcFilePath)  # all bytes

                    user.UserName = userMMKVSetting["86"]
                    user.NickName = userMMKVSetting["88"]
                    # 本机user没有AliasName, 如下值可能是修改后的UserName?
                    #user.AliasName = userMMKVSetting["87"]

                    user.Headimgurl = userMMKVSetting["headimgurl"]
                    user.HeadImgUrlHD = userMMKVSetting["headhdimgurl"]
        user.LocalHeadImg = self.__records.getRealPathIfExistByRelativePath("Documents/{}/lastHeadImage".format(user.UserID))

        # load user all message tables [session - dbPath]
        user.MessageTables = self.loadAllMessageDBTable(user.UserID)

        return user

    def loadLoginUsers(self):
        loginUsers = {}

        loginUsers = self.__loadUsersFromMMDB(loginUsers)
        loginUsers = self.__loadUsersFromLoginInfo2(loginUsers)

        for userID in loginUsers:
            self.__loadUserDetailsFromMMsetting(loginUsers[userID])
        return loginUsers
    
    def __getAllMessageDBPaths(self, userID):
        msgDBRecords = self.__records.getRecordsByFilter(
            lambda record: record[1].startswith("Documents/{}/DB/message_".format(userID)) and record[1].endswith(".sqlite"))

        msgDBPaths = []
        for record in msgDBRecords:
            msgDBPaths.append(self.__records.getRealPathByRelativePath(record[1]))

        dbPath = self.__records.getRealPathByRelativePath("Documents/{}/DB/MM.sqlite".format(userID))
        if dbPath != None:
            msgDBPaths.append(dbPath)
        return msgDBPaths

    def loadAllMessageDBTable(self, userID):
        sessionToDBPaths = {}
        msgDBPaths = self.__getAllMessageDBPaths(userID)
        for msgDBPath in msgDBPaths:
            allMsgTables = sqliteDBReader(msgDBPath, "SELECT name FROM sqlite_master WHERE type='table' and name like 'Chat_%%'")
            if len(allMsgTables) > 0:
                for msgTables in allMsgTables:
                    sessionID = msgTables[0].replace("Chat_", "")
                    if sessionID not in sessionToDBPaths:
                        sessionToDBPaths[sessionID] = msgDBPath
                    else:
                        print("multi session found: {}".format(msgTables))
        return sessionToDBPaths

    def loadMsgInfoFromDBPath(self, friendID, dbPath):
        # table must be exist in dbPath
        recordInfo = sqliteDBReader(dbPath, "select count(*), MIN(CreateTime), MAX(CreateTime) from Chat_{}".format(friendID))
        return {
            "dbPath": dbPath,
            "count": recordInfo[0][0],
            "beginTime": "" if recordInfo[0][0] == 0 else recordInfo[0][1],
            "endTime": "" if recordInfo[0][0] == 0 else recordInfo[0][2]
        }

    #def loadMsgInfoForSession(self, userID, friendID):
    #    msgDBPaths = self.__getMessageDBPaths(userID)
    #    for msgDBPath in msgDBPaths:
    #        tableExist = sqliteDBReader(msgDBPath, "SELECT name FROM sqlite_master WHERE type='table' and name = 'Chat_{}'".format(friendID))
    #        if len(tableExist) > 0:
    #            recordInfo = sqliteDBReader(msgDBPath, "select count(*), MIN(CreateTime), MAX(CreateTime) from Chat_{}".format(friendID))
    #            if len(recordInfo) > 0:
    #                return {
    #                    "dbPath": msgDBPath,
    #                    "count": recordInfo[0][0],
    #                    "beginTime": recordInfo[0][1],
    #                    "endTime": recordInfo[0][2]
    #                }
    #    return None

    def loadChatRoomMembers(self, user, session):
        members = {}
        contactDBPath = self.__records.getRealPathByRelativePath("Documents/{}/DB/WCDB_Contact.sqlite".format(user.UserID))
        if contactDBPath != None:
            print("WCDB_Contact.sqlite for user {} is : {}".format(user.UserID, contactDBPath))
            friendRow = sqliteDBReader(contactDBPath, "SELECT dbContactChatRoom FROM Friend where userName='{}'".format(session.UserName))
            if len(friendRow) > 0:
                contactsInChatRoom = WeChatProtoReader().toJson(friendRow[0][0])
                # [ToDo - Cannot parse xml RoomData]
                if "1" in contactsInChatRoom:
                    memberUserNames = contactsInChatRoom["1"].decode("utf-8").split(";")
                    friends = self.loadFriendsDetailsFromContact(user, memberUserNames)
                    for f in friends:
                        members[f.UserID] = f
        else:
            print("WCDB_Contact.sqlite not found for {}".format(user.toString()))
        return members

    def loadFriendsDetailsFromContact(self, user, friendNames):
        friends = []
        contactDBPath = self.__records.getRealPathByRelativePath("Documents/{}/DB/WCDB_Contact.sqlite".format(user.UserID))
        if contactDBPath != None:
            friendsRow = sqliteDBReader(contactDBPath, "SELECT userName,dbContactRemark,dbContactChatRoom,dbContactHeadImage,type FROM Friend where userName in ('{}')".format(
                "','".join(friendNames)))
            for friendRow in friendsRow:
                remarkField = WeChatProtoReader().toJson(friendRow[1])
                friend = User()

                friend.UserID = userNameToUserID(friendRow[0])
                friend.UserName = friendRow[0]
                friend.NickName = remarkField["1"].decode("utf8") if "1" in remarkField else ""
                friend.AliasName = remarkField["3"].decode("utf8") if "3" in remarkField else ""

                friend.LocalHeadImg = self.__sharedRecords.getRealPathIfExistByRelativePath("share/{}/session/headImg/{}.pic".format(user.UserID, friend.UserID))

                imageField = WeChatProtoReader().toJson(friendRow[3])
                friend.HeadImgUrl = imageField["2"].decode("utf8") if "2" in imageField else ""
                friend.HeadImgUrlHD = imageField["3"].decode("utf8") if "3" in imageField else ""
                friends.append(friend)
        return friends

    def loadUserSessionList(self, user, skipZeroMsgRecord=True):
        sessionsDBPath = self.__records.getRealPathByRelativePath("Documents/{}/session/session.db".format(user.UserID))
        sessionRows = sqliteDBReader(sessionsDBPath, "SELECT ConStrRes1,CreateTime,unreadcount,UsrName FROM SessionAbstract")

        sessions = []
        for sessionRow in sessionRows:
            # ConStrRes1: /session/data/c1/96266f837d14e0b693f961bee37b66, in case ConStrRes1 is none, construct that path by userID = md5(UsrName)
            sessionID = userNameToUserID(sessionRow[3])

            session = Session()
            session.UserID = sessionID
            session.UserName = sessionRow[3]
            session.BeginTime = formatDatetime(sessionRow[1])
            session.RecordCount = 0

            conStrRes1 = sessionRow[0]
            if conStrRes1 == None:
                conStrRes1 = "/session/data/{}/{}".format(sessionID[0:2], sessionID[2:])

            fileContent = self.__records.getFileAsRawByRelativePath("Documents/{}{}".format(user.UserID, conStrRes1))
            if fileContent != None:
                sessionInfo = WeChatProtoReader().toJson(fileContent)

                session.NickName = sessionInfo["1.1.4"].decode("utf8") if ("1.1.4" in sessionInfo) else ""
                session.AliasName = sessionInfo["1.1.6"].decode("utf8") if ("1.1.6" in sessionInfo) else ""
                session.HeadImgUrl = sessionInfo["1.1.14"].decode("utf8") if ("1.1.14" in sessionInfo) else ""
                session.HeadImgUrlHD = sessionInfo["1.1.15"].decode("utf8") if ("1.1.15" in sessionInfo) else ""
                session.RecordCount = sessionInfo["2.2"]
                session.EndTime = formatDatetime(sessionInfo["2.7"])
            else:
                friends = self.loadFriendsDetailsFromContact(user, [session.UserName])
                if len(friends) == 1:
                    session.NickName = friends[0].NickName
                    session.AliasName = friends[0].AliasName
                else:
                    print("connot find friend: {}, or find more that 1, size: {}".format(session.UserName, len(friends)))

            session.LocalHeadImg = self.__sharedRecords.getRealPathIfExistByRelativePath("share/{}/session/headImg/{}.pic".format(user.UserID, session.UserID))

            if sessionID in user.MessageTables:
                msgInfo = self.loadMsgInfoFromDBPath(sessionID, user.MessageTables[sessionID])

                if skipZeroMsgRecord and session.RecordCount == 0 and msgInfo["count"] == 0:
                    pass
                else:
                    session.DBPath = msgInfo["dbPath"]
                    session.RecordCount = msgInfo["count"]
                    session.BeginTime = formatDatetime(msgInfo["beginTime"])
                    session.EndTime = formatDatetime(msgInfo["endTime"])

                    sessions.append(session)
            else:
                print("message table not exist for {}".format(session.DisplayName))

        # universal sessions
        return sessions
    
    def loadMessagesByPage(self, dbPath, tableName, page, count):
        return sqliteDBReader(dbPath, "select CreateTime,Message,Des,Type,MesLocalID from {} ORDER BY CreateTime limit {} offset {}".format(
            tableName, count, count * (page - 1)))
    
    def loadMessagesByType(self, dbPath, tableName, type):
        return sqliteDBReader(dbPath, "select CreateTime,Message,Des,Type,MesLocalID from {} where Type = {} ORDER BY CreateTime".format(
            tableName, type))
    
    def loadAllMessageByType(self, dbPath, tableName, type):
        return sqliteDBReader(dbPath, "select CreateTime,Message,Des,Type,MesLocalID from {} where Type = {}".format(tableName, type))
