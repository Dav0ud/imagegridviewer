# -*- coding: utf-8 -*-
"""
This is an image grid viewer 

First argument must be the prefix path that is identical for the whole set
of images.

The second argument the 

@author Davoud Shahlaei
"""

from PyQt5.QtWidgets import QWidget, QFrame, QGridLayout, QLabel, QApplication
from PyQt5.QtGui import QPixmap,QPainter
from PyQt5.QtCore import Qt,QPoint
import sys

class ImageGrid(QWidget):
    listOfSuffix = [] # including extensions
    
    prePath = ""      # only path and basename without extebsion. 
    
    def __init__(self, prePath=None,listOfSuffix = None ):
        super().__init__()
        if prePath is not None:
            self.prePath = prePath
        if listOfSuffix is not None:
            self.listOfSuffix = listOfSuffix
        self.initUI()
        

    def initUI(self):      
        layout = QGridLayout(self)
        row = 0
        col = 0
        for p in self.listOfSuffix :
            label = Label(self.prePath + p.rstrip(), QPoint(0,0))
            layout.addWidget(label,row,col)
            col+=1
            if col > 3:
                row+=1
                col = 0
            
        self.resize(600, 400)
        self.move(30, 20)
        self.setWindowTitle(self.prePath)
        self.show()
        
class Label(QLabel):
    point = QPoint(0,0)
    def __init__(self, img, point = None):
        if point is not None:
            self.point = point
        super(Label, self).__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.pixmap = QPixmap(img)

    def paintEvent(self, event):# to display scalable images
        size = self.size()
        painter = QPainter(self)
        scaledPix = self.pixmap.scaled(size, Qt.KeepAspectRatio, 
                                       transformMode = Qt.SmoothTransformation)
        #painting the label from left upper corner
        self.point.setX((size.width() - scaledPix.width())/2)
        self.point.setY((size.height() - scaledPix.height())/2)
        painter.drawPixmap(self.point, scaledPix)
    
      
        
        
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    # suffix
    suffixFilePath = "./igridvu_suffix.txt"
    
    if len(sys.argv) < 2 :
        print("USAGE: igridvu [image file without '.{extension}'] [optional: suffixfile]")
        sys.exit()
        
    if len(sys.argv) > 2 :
        print(str(sys.argv[2]))
        suffixFilePath = str(sys.argv[2])
        
        
    suffixFile = open(suffixFilePath, 'r')
    listOfSuffix = list(suffixFile)
    suffixFile.close()   
    ex = ImageGrid(str(sys.argv[1]),listOfSuffix)
    sys.exit(app.exec_())
    