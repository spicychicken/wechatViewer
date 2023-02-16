from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout,
                QPushButton, QStyle, QSlider, QLabel)
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QSound, QSoundEffect
from PyQt5.QtMultimediaWidgets import QVideoWidget
from iOSWeChatBackupTools import *

class WechatMediaViewer(QDialog):
    def __init__(self, parent, msg):
        QDialog.__init__(self, parent)
        self.message = msg
        self.__createView()

    def __createImageView(self):
        self.imageLabel = QLabel()

        if self.message["type"] == "image":
            pixmap = QPixmap(self.message["src"])
            self.imageLabel.setFixedSize(pixmap.width(), pixmap.height())
            self.imageLabel.setPixmap(pixmap)
        else:
            self.movie = QMovie(self.message["src"])
            self.imageLabel.setMovie(self.movie)
            self.movie.start()
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.imageLabel)

        self.setLayout(vbox)

        self.setWindowTitle("打开图片")

    def __createVideoView(self):
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.Flag.VideoSurface)
        videoWidget = QVideoWidget()

        if self.message["type"] == "video":
            videoWidget.setFixedSize(self.message["width"], self.message["height"])
        else:
            videoWidget.setFixedSize(400, 20)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playWeChatMedia)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setMediaPlayPosition)

        controlHBox = QHBoxLayout()
        controlHBox.setContentsMargins(0, 0, 0, 0)
        controlHBox.addWidget(self.playButton)
        controlHBox.addWidget(self.positionSlider)
        
        vbox = QVBoxLayout()
        vbox.addWidget(videoWidget)
        vbox.addLayout(controlHBox)

        self.setLayout(vbox)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.mediaPositionChanged)
        self.mediaPlayer.durationChanged.connect(self.mediaDurationChanged)
        self.setWindowTitle("播放媒体")

        if self.message["type"] == "audio":
            path = self.__getMediaContentUrl()
            print(path)
            SilkPlayer.playBG(path)
        else:
            self.mediaPlayer.setMedia(QMediaContent(self.__getMediaContentUrl()))
            self.playButton.setEnabled(True)
            self.playWeChatMedia()

    def __getMediaContentUrl(self):
        print(self.message["src"])
        if self.message["type"] == "audio":
            return SilkConvert().convert(self.message["src"])
        else:
            return QUrl(self.message["src"])

    def __createView(self):
        if self.message["type"] == "image" or self.message["type"] == "gif":
            self.__createImageView()
        else:
            self.__createVideoView()

    def playWeChatMedia(self):
        if self.mediaPlayer.state() == QMediaPlayer.State.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def setMediaPlayPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.State.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def mediaPositionChanged(self, position):
        self.positionSlider.setValue(position)

    def mediaDurationChanged(self, duration):
        self.positionSlider.setRange(0, duration)