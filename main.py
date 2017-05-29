from tkinter import *
from tkinter.ttk import *
import tkinter.messagebox
from PIL import Image, ImageTk
import os
import glob
import random
import numpy as np
import parse
import io

# colors for the bboxes
COLORS = ['red', 'blue']
# image sizes for the examples
SIZE = 256, 256


def complete_rectangle_with_projection_point(x1, y1, x2, y2, xr, yr):
    with np.errstate(divide='ignore', invalid='ignore'):
        m = np.true_divide(y2 - y1, x2 - x1)
        m_perp = np.true_divide(-1, m)

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
        self.parent.title("Rectangle Labeling")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=FALSE, height=FALSE)

        # initialize global state
        self.image_base_directory = "Images"
        self.image_list = []
        self.example_base_directory = "Examples"
        self.example_list = []
        self.label_base_directory = "Labels"
        self.label_list = []
        self.cur = 0
        self.total = 0
        self.user_dataset_directory = ""
        self.tkimg = None
        self.rectangle_listbox_index = 0
        self.rectangle_listbox_index_cycle = False

        # initialize mouse state
        self.click_state = 1

        # reference to rectangle
        self.cur_rectangle_coordinates = [
            (None, None), (None, None), (None, None), (None, None)]
        self.rectangle_ids_list = []
        self.rectangle_coordinates_list = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text="Image Dir:")
        self.label.grid(row=0, column=0, sticky=E)
        self.entry = Entry(self.frame)
        self.entry.grid(row=0, column=1, sticky=W + E)
        self.load_button = Button(
            self.frame,
            text="Load",
            command=self.load_directory)
        self.load_button.grid(row=0, column=2, sticky=W + E)

        # main panel for labeling
        self.main_panel = Canvas(self.frame, cursor='tcross')
        self.main_panel.bind("<Button-1>", self.mouse_click)
        self.main_panel.bind("<Motion>", self.mouse_move)
        self.parent.bind("<Escape>", self.cancel_rectangle)
        self.parent.bind("a", self.previous_image)
        self.parent.bind("d", self.next_image)
        self.main_panel.grid(row=1, column=1, rowspan=5, sticky=W + N)

        # showing bbox info & delete bbox
        self.rectangle_label = Label(self.frame, text='Rectangles:')
        self.rectangle_label.grid(row=1, column=2, sticky=W + N)
        self.rectangle_listbox = Listbox(self.frame, width=50, height=12)
        self.rectangle_listbox.grid(row=2, column=2, sticky=N)
        self.rectangle_listbox.bind(
            '<<ListboxSelect>>',
            self.rectangle_listbox_onselect)

        self.rectangle_delete_button = Button(
            self.frame, text='Delete (x)', command=self.delete_rectangle)
        self.rectangle_delete_button.grid(row=3, column=2, sticky=W + E + N)
        self.parent.bind("x", self.delete_rectangle)

        self.rectangle_clear_button = Button(
            self.frame, text='Save (s)', command=self.save_image)
        self.rectangle_clear_button.grid(row=4, column=2, sticky=W + E + N)
        self.parent.bind("s", self.save_image)

        self.rectangle_print_button = Button(
            self.frame, text='Print (p)', command=self.print_main_panel)
        self.rectangle_print_button.grid(row=5, column=2, sticky=W + E + N)
        self.parent.bind("p", self.print_main_panel)
        

        # control panel for image navigation
        self.navigation_control_panel = Frame(self.frame)
        self.navigation_control_panel.grid(
            row=6, column=1, columnspan=2, sticky=W + E)
        self.previous_image_button = Button(
            self.navigation_control_panel,
            text='<< Prev (a)',
            width=10,
            command=self.previous_image)
        self.previous_image_button.pack(side=LEFT, padx=5, pady=3)
        self.next_image_button = Button(
            self.navigation_control_panel,
            text='Next (d) >>',
            width=10,
            command=self.next_image)
        self.next_image_button.pack(side=LEFT, padx=5, pady=3)
        self.image_progression_label = Label(
            self.navigation_control_panel,
            text="Progress:     /    ")
        self.image_progression_label.pack(side=LEFT, padx=5)
        self.goto_image_label = Label(
            self.navigation_control_panel,
            text="Go to Image No.")
        self.goto_image_label.pack(side=LEFT, padx=5)
        self.goto_image_index_entry = Entry(
            self.navigation_control_panel, width=5)
        self.goto_image_index_entry.pack(side=LEFT)
        self.goto_image_button = Button(
            self.navigation_control_panel,
            text='Go',
            command=self.goto_image)
        self.goto_image_button.pack(side=LEFT)

        # example pannel for illustration
        self.example_panel = Frame(self.frame, border=10)
        self.example_panel.grid(row=1, column=0, rowspan=5, sticky=N)
        self.example_panel_label = Label(self.example_panel, text="Examples:")
        self.example_panel_label.pack(side=TOP, pady=5)
        self.example_panel_example_labels = []
        for i in range(3):
            self.example_panel_example_labels.append(Label(self.example_panel))
            self.example_panel_example_labels[-1].pack(side=TOP)

        # mouse position
        self.mouse_position_label = Label(
            self.navigation_control_panel, text='')
        self.mouse_position_label.pack(side=RIGHT)
        
        # image path
        self.image_path_label = Label(self.frame, text="")
        self.image_path_label.grid(row=6, column=0, sticky=W)
        
        # frame configuration
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(5, weight=1)

    def erase_rectangle(self, ids):
        for i in ids:
            self.main_panel.delete(i)

    def plot_rectangle(self, rectangle, width=2, add_ids=True):
        [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] = rectangle
        hl1 = self.main_panel.create_line(
            x1, y1, x2, y2, width=width, fill=COLORS[0])
        hl2 = self.main_panel.create_line(
            x2, y2, x3, y3, width=width, fill=COLORS[1])
        hl3 = self.main_panel.create_line(
            x3, y3, x4, y4, width=width, fill=COLORS[0])
        hl4 = self.main_panel.create_line(
            x4, y4, x1, y1, width=width, fill=COLORS[1])
        ids = [hl1, hl2, hl3, hl4]
        if add_ids:
            self.rectangle_ids_list.append(ids)

        return ids

    def append_rectangle(self, rectangle):
        self.rectangle_coordinates_list.append(list(rectangle))
        self.rectangle_listbox.insert(END, str(rectangle))

    def rectangle_listbox_onselect(self, event):
        if len(self.rectangle_ids_list) == 0:
            return

        prev_index = self.rectangle_listbox_index
        self.erase_rectangle(self.rectangle_ids_list[prev_index])
        rectangle = self.rectangle_coordinates_list[prev_index]
        ids = self.plot_rectangle(rectangle, width=2, add_ids=False)
        self.rectangle_ids_list[prev_index] = ids

        w = event.widget
        self.rectangle_listbox_index = int(w.curselection()[0])
        index = self.rectangle_listbox_index
        self.erase_rectangle(self.rectangle_ids_list[index])
        rectangle = self.rectangle_coordinates_list[index]
        if index != prev_index:
            ids = self.plot_rectangle(rectangle, width=6, add_ids=False)
            self.rectangle_listbox_index_cycle = False
        else:
            if self.rectangle_listbox_index_cycle:
                ids = self.plot_rectangle(rectangle, width=2, add_ids=False)
                self.rectangle_listbox_index_cycle = False
            else:
                ids = self.plot_rectangle(rectangle, width=6, add_ids=False)
                self.rectangle_listbox_index_cycle = True
        self.rectangle_ids_list[index] = ids

    def load_directory(self, dbg=False):
        self.user_dataset_directory = self.entry.get()
        self.parent.focus()

        # get image list
        image_directory = os.path.join(
            self.image_base_directory, self.user_dataset_directory)
        self.image_list = glob.glob(
            os.path.join(image_directory, '**', '*.jpg'),
            recursive=True)
        if len(self.image_list) == 0:
            print('No .jpg images found in the specified dir!')
            return
        
        # set label list
        for imagepath in self.image_list:
            labelpath = imagepath.split(os.path.sep)
            labelpath[0] = self.label_base_directory
            labelpath[-1] = labelpath[-1].replace('.jpg', '.txt')
            os.makedirs(os.path.sep.join(labelpath[:-1]), exist_ok=True)
            labelpath = os.path.sep.join(labelpath)
            self.label_list.append(labelpath)

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.image_list)

        # load example bboxes
        example_directory = os.path.join(
            self.example_base_directory, self.user_dataset_directory)
        if os.path.exists(example_directory):

            filelist = glob.glob(
                os.path.join(example_directory, '**', '*.jpg'),
                recursive=True)
            self.tmp = []
            self.example_list = []
            random.shuffle(filelist)
            for (i, f) in enumerate(filelist):
                if i == 3:
                    break
                im = Image.open(f)
                r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
                new_size = int(r * im.size[0]), int(r * im.size[1])
                self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
                self.example_list.append(ImageTk.PhotoImage(self.tmp[-1]))
                self.example_panel_example_labels[i].config(
                    image=self.example_list[-1],
                    width=SIZE[0]) 
                    #height=SIZE[1]

        self.load_image()
        print("{} images loaded from {}".format(
            self.total, 
            self.user_dataset_directory))

    def load_image(self):
        # load image
        image_filename = self.image_list[self.cur - 1]
        self.image_path_label.config(text=image_filename)
        self.img = Image.open(image_filename)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.main_panel.config(
            #width=max(self.tkimg.width(), 400),
            #height=max(self.tkimg.height(), 400)
            width=self.tkimg.width(),
            height=self.tkimg.height()
        )
        self.main_panel.create_image(0, 0, image=self.tkimg, anchor=NW)
        self.image_progression_label.config(
            text="%04d/%04d" %
            (self.cur, self.total))
        
        # load labels
        self.clear_rectangle()
        label_filename = self.label_list[self.cur - 1]

        with open(label_filename, 'r') as f:
            for (i, line) in enumerate(f):
                [x1, y1, x2, y2, x3, y3, x4, y4] = [
                    int(t.strip()) for t in line.split()]
                rectangle = [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
                self.append_rectangle(rectangle)
                self.plot_rectangle(rectangle)

    def mouse_click(self, event):
        x = int(np.round(event.x))
        y = int(np.round(event.y))
        if self.click_state == 1:
            self.cur_rectangle_coordinates[0] = x, y
            self.click_state = 2
        elif self.click_state == 2:
            self.cur_rectangle_coordinates[1] = x, y
            self.click_state = 3
        elif self.click_state == 3:
            x1, y1 = self.cur_rectangle_coordinates[0]
            x2, y2 = self.cur_rectangle_coordinates[1]
            x3, y3, x4, y4 = complete_rectangle_with_projection_point(
                x1, y1, x2, y2, x, y)
            x3 = int(np.round(x3))
            y3 = int(np.round(y3))
            x4 = int(np.round(x4))
            y4 = int(np.round(y4))
            self.cur_rectangle_coordinates[2] = x3, y3
            self.cur_rectangle_coordinates[3] = x4, y4
            self.plot_rectangle(self.cur_rectangle_coordinates)
            self.append_rectangle(self.cur_rectangle_coordinates)
            self.click_state = 1
        else:
            self.click_state = 1

    def mouse_move(self, event):
        x = event.x
        y = event.y
        x1, y1 = self.cur_rectangle_coordinates[0]
        x2, y2 = self.cur_rectangle_coordinates[1]
        self.mouse_position_label.config(text='x: %d, y: %d' % (x, y))
        if self.tkimg:
            if self.click_state == 1:
                if self.hl:
                    self.main_panel.delete(self.hl)
                if self.vl:
                    self.main_panel.delete(self.vl)
            elif self.click_state == 2:
                if self.hl:
                    self.main_panel.delete(self.hl)
                self.hl = self.main_panel.create_line(
                    x1, y1, x, y, width=2, fill=COLORS[0])
            elif self.click_state == 3:
                if self.vl:
                    self.main_panel.delete(self.vl)
                x3, y3, x4, y4 = complete_rectangle_with_projection_point(
                    x1, y1, x2, y2, x, y)
                self.vl = self.main_panel.create_line(
                    x2, y2, x3, y3, width=2, fill=COLORS[1])

    def cancel_rectangle(self, event=None):
        if self.click_state > 1:
            if self.hl:
                self.main_panel.delete(self.hl)
            if self.vl:
                self.main_panel.delete(self.vl)
            self.click_state = 1

    def delete_rectangle(self, event=None):
        sel = self.rectangle_listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.erase_rectangle(self.rectangle_ids_list[idx])
        self.rectangle_ids_list.pop(idx)
        self.rectangle_coordinates_list.pop(idx)
        self.rectangle_listbox.delete(idx)
        if self.rectangle_listbox_index >= idx and not self.rectangle_listbox_index == 0:
            self.rectangle_listbox_index = self.rectangle_listbox_index - 1

    def clear_rectangle(self):
        for idx in range(len(self.rectangle_ids_list)):
            for i in self.rectangle_ids_list[idx]:
                self.main_panel.delete(i)
        self.rectangle_listbox.delete(0, len(self.rectangle_coordinates_list))
        self.rectangle_ids_list = []
        self.rectangle_coordinates_list = []
        self.rectangle_listbox_index = 0

    def previous_image(self, event=None):
        self.save_image()
        if self.cur > 1:
            self.cur -= 1
        else:
            self.cur = self.total
        self.load_image()

    def next_image(self, event=None):
        self.save_image()
        if self.cur < self.total:
            self.cur += 1
        else:
            self.cur = 1
        self.load_image()

    def goto_image(self):
        idx = int(self.goto_image_index_entry.get())
        if 1 <= idx and idx <= self.total:
            self.save_image()
            self.cur = idx
            self.load_image()

    def save_image(self, event=None):
        label_filename = self.label_list[self.cur - 1]
        with open(label_filename, 'w') as f:
            for rectangle in self.rectangle_coordinates_list:
                [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] = rectangle
                entry = "{} {} {} {} {} {} {} {}\n".format(
                    x1, y1, x2, y2, x3, y3, x4, y4)
                f.write(entry)
        print('Image No. %d saved' % (self.cur))

    def print_main_panel(self, event=None):
        self.main_panel.update()
        labeled_image_filename = self.label_list[self.cur - 1]
        labeled_image_filename = labeled_image_filename.replace(
            '.txt', 
            '_labeled.jpg')
        print("Printing image to {}".format(labeled_image_filename))
        ps = self.main_panel.postscript(colormode="color")
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        img.save(labeled_image_filename)


if __name__ == '__main__':
    root = Tk()
    Style().theme_use('alt')
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
