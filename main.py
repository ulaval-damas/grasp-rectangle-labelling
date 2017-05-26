#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
#-------------------------------------------------------------------------------

from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import os
import glob
import random
import numpy as np
import parse

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256

def complete_rectangle_with_projection_point(x1, y1, x2, y2, xr, yr):
    m = (y2 - y1) / (x2 - x1)
    m_perp = -1/m
    
    if m == 0:
        x3 = x2
        y3 = yr
        
        x4 = x1
        y4 = yr
        
    elif m_perp == 0:
        x3 = xr
        y3 = y2
        
        x4 = xr
        y4 = y1
        
    else:
        x3 = (yr - y2 + m_perp * x2 - m * xr) / (m_perp - m)
        y3 = y2 + m_perp * (x3 - x2)
        
        l = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        if y2 > y1:
            y4 = y3 - np.sqrt((m**2 * l**2) / (1 + m**2))
        else:
            y4 = y3 + np.sqrt((m**2 * l**2) / (1 + m**2))
        
        x4 = x3 + (y4 - y3) / m
    
    return x3, y3, x4, y4



class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 1
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.grasp_rectangle_ids_list = []
        self.grasp_rectangle_ids = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2, sticky = W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 4, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 1, column = 2,  sticky = W+N)
        self.listbox = Listbox(self.frame, width = 40, height = 12)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.listbox.bind('<<ListboxSelect>>', self.listbox_onselect)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 4, column = 2, sticky = W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 5, column = 1, columnspan = 2, sticky = W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border = 10)
        self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        self.tmpLabel2.pack(side = TOP, pady = 5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        # for debugging
##        self.setImage()
##        self.loadDir()
    
    def plot_rectangle(self, x1, y1, x2, y2, x3, y3, x4, y4, width=2):
        if self.grasp_rectangle_ids:
            for i in self.grasp_rectangle_ids:
                self.mainPanel.delete(i)
        
        hl1 = self.mainPanel.create_line(x1, y1, x2, y2, width=width, fill=COLORS[0])
        hl2 = self.mainPanel.create_line(x2, y2, x3, y3, width=width, fill=COLORS[1])
        hl3 = self.mainPanel.create_line(x3, y3, x4, y4, width=width, fill=COLORS[0])
        hl4 = self.mainPanel.create_line(x4, y4, x1, y1, width=width, fill=COLORS[1])
        self.grasp_rectangle_ids = (hl1, hl2, hl3, hl4)
        self.grasp_rectangle_ids_list.append(self.grasp_rectangle_ids)
        self.grasp_rectangle_ids = None
    
    
    def save_rectangle(self, x1, y1, x2, y2, x3, y3, x4, y4):
        self.bboxList.append((x1, y1, x2, y2, x3, y3, x4, y4))
        self.listbox.insert(END, '(%d, %d), (%d, %d), (%d, %d), (%d, %d)' %(x1, y1, x2, y2, x3, y3, x4, y4))
        #self.listbox.itemconfig(len(self.grasp_rectangle_ids_list) - 1, fg=COLORS[(len(self.grasp_rectangle_ids_list) - 1) % len(COLORS)])
    
    def listbox_onselect(self, event):
        w = event.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        print('You selected item %d: "%s"' % (index, value))

    def loadDir(self, dbg = False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = int(s)
        else:
            s = r'D:\workspace\python\labelGUI'
##        if not os.path.isdir(s):
##            tkMessageBox.showerror("Error!", message = "The specified dir doesn't exist!")
##            return
        # get image list
        self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageList = glob.glob(os.path.join(self.imageDir, '*.jpg'))
        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        self.outDir = os.path.join(r'./Labels', '%03d' %(self.category))
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        # load example bboxes
        self.egDir = os.path.join(r'./Examples', '%03d' %(self.category))
        if not os.path.exists(self.egDir):
            return
        filelist = glob.glob(os.path.join(self.egDir, '*.JPEG'))
        self.tmp = []
        self.egList = []
        random.shuffle(filelist)
        for (i, f) in enumerate(filelist):
            if i == 3:
                break
            im = Image.open(f)
            r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
            new_size = int(r * im.size[0]), int(r * im.size[1])
            self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
            self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
            self.egLabels[i].config(image = self.egList[-1], width = SIZE[0], height = SIZE[1])

        self.loadImage()
        print('%d images loaded from %s' %(self.total, s))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    if i == 0:
                        bbox_cnt = int(line.strip())
                        continue
                    tmp = [float(t.strip()) for t in line.split()]
                    self.save_rectangle(*tmp)
                    self.plot_rectangle(*tmp)

    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxList))
            for bbox in self.bboxList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' %(self.cur))

    
    def mouseClick(self, event):
        if self.STATE['click'] == 1:
            self.STATE['x1'], self.STATE['y1'] = event.x, event.y
            self.STATE['click'] = 2
        elif self.STATE['click'] == 2:
            self.STATE['x2'], self.STATE['y2'] = event.x, event.y
            self.STATE['click'] = 3
        elif self.STATE['click'] == 3:
            xr = event.x
            yr = event.y
            x1 = self.STATE['x1']
            y1 = self.STATE['y1']
            x2 = self.STATE['x2']
            y2 = self.STATE['y2']
            x3, y3, x4, y4 = complete_rectangle_with_projection_point(x1, y1, x2, y2, xr, yr)
            self.plot_rectangle(x1, y1, x2, y2, x3, y3, x4, y4)
            self.save_rectangle(x1, y1, x2, y2, x3, y3, x4, y4)
            self.STATE['click'] = 1
        else:
            self.STATE['click'] = 1


    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.STATE['click'] == 1:
                if self.hl:
                    self.mainPanel.delete(self.hl)
                if self.vl:
                    self.mainPanel.delete(self.vl)
            if self.STATE['click'] == 2:
                if self.hl:
                    self.mainPanel.delete(self.hl)
                self.hl = self.mainPanel.create_line(self.STATE['x1'], self.STATE['y1'], event.x, event.y, width = 2, fill=COLORS[0])
            elif self.STATE['click'] == 3:
                if self.vl:
                    self.mainPanel.delete(self.vl)
                xr = event.x
                yr = event.y
                x1 = self.STATE['x1']
                y1 = self.STATE['y1']
                x2 = self.STATE['x2']
                y2 = self.STATE['y2']
                x3, y3, x4, y4 = complete_rectangle_with_projection_point(x1, y1, x2, y2, xr, yr)
                self.vl = self.mainPanel.create_line(x2, y2, x3, y3, width=2, fill=COLORS[1])
                
    
    def cancelBBox(self, event):
        if self.STATE['click'] > 1:
            if self.grasp_rectangle_ids:
                for i in self.grasp_rectangle_ids:
                    self.mainPanel.delete(i)
                self.grasp_rectangle_ids = None
                self.STATE['click'] = 1

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        for i in self.grasp_rectangle_ids_list[idx]:
            self.mainPanel.delete(i)
        self.grasp_rectangle_ids_list.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)


    def clearBBox(self):
        for idx in range(len(self.grasp_rectangle_ids_list)):
            for i in self.grasp_rectangle_ids_list[idx]:
                self.mainPanel.delete(i)
        self.listbox.delete(0, len(self.bboxList))
        self.grasp_rectangle_ids_list = []
        self.bboxList = []


    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

##    def setImage(self, imagepath = r'test2.png'):
##        self.img = Image.open(imagepath)
##        self.tkimg = ImageTk.PhotoImage(self.img)
##        self.mainPanel.config(width = self.tkimg.width())
##        self.mainPanel.config(height = self.tkimg.height())
##        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width =  True, height = True)
    root.mainloop()
