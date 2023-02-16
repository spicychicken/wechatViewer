from iOSWeChatBackupReader import *
from weChatModel import *
import os
from urllib import request

class WeChatResources:
    def __init__(self):
        self.basePath = os.getcwd() + "\\resources\\"
        self.headImgPath = self.basePath + "\\head\\"
        self.emoticonImgPath = self.basePath + "\\emoticon\\"
        self.defaultHead = self.headImgPath + "DefaultProfileHead@2x.png"

    def getDisplayHeadImg(self, user, download = False):
        if user.LocalHeadImg:
            return user.LocalHeadImg

        if download:
            return self.downloadHead(user)
        else:
            return self.defaultHead
    
    def downloadHead(self, user):
        downloadHeadImg = self.headImgPath + user.UserID + ".png"
        if os.path.exists(downloadHeadImg):
            return downloadHeadImg

        if user.HeadImgUrlHD == "" and user.HeadImgUrl == "":
            return self.defaultHead

        try:
            if user.HeadImgUrlHD:
                request.urlretrieve(user.HeadImgUrlHD, downloadHeadImg)
            elif user.HeadImgUrl:
                request.urlretrieve(user.HeadImgUrl, downloadHeadImg)
        except Exception as e:
            print(user.HeadImgUrlHD)

        return downloadHeadImg

    def downloadEmoticon(self, url, name):
        downloadEmoticonImg = self.emoticonImgPath + name
        if os.path.exists(downloadEmoticonImg):
            return downloadEmoticonImg

        request.urlretrieve(url, downloadEmoticonImg)
        return downloadEmoticonImg