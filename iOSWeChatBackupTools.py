import sqlite3
import plistlib
import biplist
import datetime
from lxml import etree

class IOSBackupManifestDBRecords:
    def __init__(self, basePath, records):
        self.__basePath = basePath
        self.__records = records
        self.__createIndex()
    
    # fileID,relativePath,flags,file
    def __createIndex(self):
        self._fileIndexs = {}
        for i in range(0, len(self.__records)):
            self._fileIndexs[self.__records[i][1]] = i
    
    def __combineBasePathAndFileID(self, fileID):
        return self.__basePath + "/" + fileID[0:2] + "/" + fileID

    def getRecordByRelativePath(self, relativePath):
        if relativePath in self._fileIndexs:
            return self.__records[self._fileIndexs[relativePath]]
        return None

    def getRecordsByFilter(self, filterFn):
        return list(filter(filterFn, self.__records))

    def getRealPathByRelativePath(self, relativePath):
        record = self.getRecordByRelativePath(relativePath)
        if record != None:
            return self.__combineBasePathAndFileID(record[0])
        return None
    
    def getRealPathIfExistByRelativePath(self, relativePath):
        record = self.getRecordByRelativePath(relativePath)
        if record != None:
            realPath = self.__combineBasePathAndFileID(record[0])
            if os.path.exists(realPath):
                return realPath
        return None

    def ifRealPathExistByRelativePath(self, relativePath):
        realPath = self.getRealPathByRelativePath(relativePath)
        if realPath != None:
            return os.path.exists(realPath)
        return False

    def getFileAsRawByRelativePath(self, relativePath, mode="rb"):
        filePath = self.getRealPathByRelativePath(relativePath)
        if filePath != None:
            with open(filePath, mode) as fp:
                return fp.read()
        return None

    def __readFileByPlistType(self, filePath, mode="rb", readType="plist"):
        if readType == "plist":
            with open(filePath, mode) as fp:
                return plistlib.load(fp)
        else:
            return biplist.readPlist(filePath)

    # plist or biplist
    def getFilesAsPlistByFilter(self, filterFn, mode="rb", readType="plist"):
        records = self.getRecordsByFilter(filterFn)
        
        infoPLs = []
        for record in records:
            filePath = self.__combineBasePathAndFileID(record[0])
            infoPLs.append(self.__readFileByPlistType(filePath, mode, readType))
        return infoPLs
    
    def getFileAsPlistByRelativePath(self, relativePath, mode="rb", readType="plist"):
        filePath = self.getRealPathByRelativePath(relativePath)
        if filePath != None:
            return self.__readFileByPlistType(filePath, mode, readType)
        return None

class IOSBackupManifestDBReader:
    def __init__(self, basePath):
        self._basePath = basePath

    # load Manifest.db
    # pssible parameter for sqlite:
    #  PRAGMA mmap_size=2097152; // 8M:8388608  2M 2097152
    #  PRAGMA synchronous=OFF;
    def loadRecordsByDomain(self, domain):
        querySQL = "SELECT fileID,relativePath,flags,file FROM Files where domain = '{}'".format(domain)
        manifestDB = sqlite3.connect(self._basePath + "/Manifest.db")
        cursor = manifestDB.cursor()
        cursor.execute(querySQL)
        records = cursor.fetchall()
        cursor.close()
        manifestDB.close()
        return IOSBackupManifestDBRecords(self._basePath, records)

def resolveBiplistUID(bipNode, rootNode = None):
    if rootNode == None:
        rootNode = bipNode["$objects"]
    if isinstance(bipNode, dict):
        for key in bipNode:
            if isinstance(bipNode[key], biplist.Uid):
                bipNode[key] = rootNode[bipNode[key].integer]
            else:
                resolveBiplistUID(bipNode[key], rootNode)
    elif isinstance(bipNode, list):
        for i in range(len(bipNode)):
            if isinstance(bipNode[i], biplist.Uid):
                bipNode[i] = rootNode[bipNode[i].integer]
            else:
                resolveBiplistUID(bipNode[i], rootNode)
    return bipNode

def sqliteDBReader(dbPath, querySQL):
    connectDB = sqlite3.connect(dbPath)
    cursor = connectDB.cursor()
    cursor.execute(querySQL)
    rows = cursor.fetchall()
    cursor.close()
    connectDB.close()
    return rows

def formatDatetime(dt):
    if isinstance(dt, datetime.datetime):
        return "{:%Y-%m-%d %H:%M:%S}".format(dt)
    else:
        return "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.fromtimestamp(dt))

# -------------------------------------------------------------------------
# handle with unknown .proto
from google.protobuf.descriptor_pb2 import FileDescriptorProto, DescriptorProto
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import MessageFactory

from warnings import catch_warnings

class WeChatProtoReader(object):
    def __init__(self):
        fdp = FileDescriptorProto(name="empty_message.proto")
        fdp.message_type.append(DescriptorProto(name="EmptyMessage"))
        dp = DescriptorPool()
        dp.Add(fdp)
        descriptor = dp.FindMessageTypeByName("EmptyMessage")

        self.emptyMsgType = MessageFactory(dp).GetPrototype(descriptor)

    def __toJson(self, proto, parentField, jsonResult):
        try:
            with catch_warnings(record=True) as caught_warnings:
                message = self.emptyMsgType()
                try:
                    message.ParseFromString(proto)
                except Exception as e:
                    message.ParseFromString(bytes("\n", "utf8") + proto)
                
                if caught_warnings:
                    message.ParseFromString(bytes("\n", "utf8") + proto)

                for unknowField in message.UnknownFields():
                    nextParentField = ("" if parentField == "" else (parentField + ".")) + str(unknowField.field_number)
                    if unknowField.wire_type == 2:
                        self.__toJson(unknowField.data, nextParentField, jsonResult)
                    else:
                        jsonResult[nextParentField] = unknowField.data
        except Exception as e:
            jsonResult[parentField] = proto

    def toJson(self, proto):
        unknowFieldsJson = {}
        self.__toJson(proto, "", unknowFieldsJson)
        return unknowFieldsJson


import os
import silkpy
import wave
import pyaudio
import threading

class SilkConvert:
    def __init__(self):
        self.tempPCMFile = os.getcwd() + "\\" + "temp_pcmfile"
        self.tempWaveFile = os.getcwd() + "\\" + "temp_wavefile.wave"

    def pcmToWave(self, pcmPath, wavePath, channels=1, bits=16, sample_rate=24000):
        pcmf = open(pcmPath, 'rb')
        pcmdata = pcmf.read()
        pcmf.close()

        wavfile = wave.open(wavePath, 'wb') # 打开将要写入的 WAVE 文件
        wavfile.setnchannels(channels)      # 设置声道数
        wavfile.setsampwidth(bits // 8)     # 设置采样位宽
        wavfile.setframerate(sample_rate)   # 设置采样率
        wavfile.writeframes(pcmdata)        # 写入 data 部分
        wavfile.close()

    def convert(self, silkPath):
        # clean old file
        if os.path.exists(self.tempPCMFile):
            os.remove(self.tempPCMFile)
        if os.path.exists(self.tempWaveFile):
            os.remove(self.tempWaveFile)

        if silkpy.decode(silkPath, self.tempPCMFile) == 1:
            self.pcmToWave(self.tempPCMFile, self.tempWaveFile)

            return self.tempWaveFile
        return None

def backgroundPlaySilk(player, filePath):
    player.play(filePath)
    player.bgTask = None

class SilkPlayer:
    def __init__(self):
        self.tempPCMFile = os.getcwd() + "\\" + "temp_pcmfile"
        self.tempWaveFile = os.getcwd() + "\\" + "temp_wavefile.wave"
        self.bgTask = None
        self.currentSilkFile = None

    def __pcmToWave(self, pcmPath, wavePath, channels=1, bits=16, sample_rate=24000):
        pcmf = open(pcmPath, 'rb')
        pcmdata = pcmf.read()
        pcmf.close()

        wavfile = wave.open(wavePath, 'wb') # 打开将要写入的 WAVE 文件
        wavfile.setnchannels(channels)      # 设置声道数
        wavfile.setsampwidth(bits // 8)     # 设置采样位宽
        wavfile.setframerate(sample_rate)   # 设置采样率
        wavfile.writeframes(pcmdata)        # 写入 data 部分
        wavfile.close()

    def convert(self, silkPath):
        # clean old file
        if os.path.exists(self.tempPCMFile):
            os.remove(self.tempPCMFile)
        if os.path.exists(self.tempWaveFile):
            os.remove(self.tempWaveFile)

        if silkpy.decode(silkPath, self.tempPCMFile) == 1:
            self.__pcmToWave(self.tempPCMFile, self.tempWaveFile)

            return self.tempWaveFile
        return None

    def play(self, silkFilePath):
        waveFilePath = self.convert(silkFilePath)

        audio = pyaudio.PyAudio()
        with wave.open(waveFilePath, "rb") as wf:
            stream = audio.open(format=pyaudio.paInt16,channels=wf.getnchannels(),rate=wf.getframerate(),output=True)

            chunk = 1024
            data = wf.readframes(chunk)
            while len(data) > 0 and self.stopPlay == False:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()

        audio.terminate()

    def playBG(self, silkFilePath):
        if self.bgTask:
            self.stopPlay = True
            self.bgTask.join()
        
        if self.currentSilkFile != silkFilePath:
            self.stopPlay = False
            self.currentSilkFile = silkFilePath
            self.bgTask = threading.Thread(target=backgroundPlaySilk, kwargs={"player": self, "filePath": silkFilePath})
            self.bgTask.start()
        else:
            self.currentSilkFile = None

class XmlParser:
    def __init__(self, xmlContent):
        self.__root = etree.XML(xmlContent)

    def getNodesByPath(self, nodePath):
        return self.__root.xpath(nodePath)

    def getNodeByPath(self, nodePath):
        pathList = self.__root.xpath(nodePath)
        if len(pathList) == 1:
            return pathList[0]
        return None

    def getAttributeValueByPath(self, nodePath, attribute):
        pathList = self.__root.xpath(nodePath + "/@" + attribute)
        if len(pathList) == 1:
            return pathList[0]
        return None

    def getNodeValueByPath(self, nodePath):
        pathList = self.__root.xpath(nodePath + "/text()")
        if len(pathList) == 1:
            return pathList[0]
        return None

import math
import re

def removeHtml(html):
    return re.compile(r'<[^>]+>').sub('', html)

BROSWER_PATH = "D:/tools/Mozilla Firefox/firefox.exe"
def openFileByBrowser(filePath):
    fileURI = "file:///" + filePath
    os.system("\"{}\" {}".format(BROSWER_PATH, fileURI))