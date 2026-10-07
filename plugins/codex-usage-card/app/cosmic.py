"""Cosmic skin for the existing read-only usage client. Windows public beta."""
from pathlib import Path
from datetime import datetime
import argparse
import ctypes
import json
import os
import tempfile
import time
import tkinter as tk
import usage_core as core
from desktop_settings import Startup, card_size, read_size, resized_ppm, settings_file

VERSION = '0.4.0'
core.VERSION = VERSION
BG, WHITE, BLUE, MUTED = '#070d17', '#edf5ff', '#92caff', '#a2b9d6'


class CanvasLabel:
    """Keep the existing refresh controller independent of the text renderer."""
    def __init__(self, canvas, x, y, text='', font=('Segoe UI', -11), anchor='w', width=0):
        self.canvas = canvas
        self.item = canvas.create_text(x, y, text=text, font=font, fill=MUTED,
                                       anchor=anchor, width=width)

    def config(self, **kwargs):
        self.canvas.itemconfigure(self.item, **{('fill' if k == 'fg' else k): v
                                                for k, v in kwargs.items()})

    def cget(self, key):
        return self.canvas.itemcget(self.item, 'fill' if key == 'fg' else key)


class CosmicWidget(core.Widget):
    WIDTH = 480

    def __init__(self, root, settings_path, status_path=None, auto_start=True, qa_frame=False):
        self.qa_frame = qa_frame
        self.ready = False
        self.scale = 1.0
        self.base_items = {}
        self.resize_job = None
        self.resize_origin = None
        super().__init__(root, settings_path, None, auto_start=False)
        self.body.destroy()
        root.title('Usage Card for Codex')
        root.attributes('-alpha', 1.0)
        self.card_width, self.card_height = read_size(settings_path, root.winfo_screenwidth(), root.winfo_screenheight())
        root.geometry(f'{self.card_width}x{self.card_height}')
        self.body = self.canvas = tk.Canvas(root, width=480, height=320, bg=BG,
                                            bd=0, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        background = Path(__file__).parent / 'assets' / 'cosmic-original.png'
        if not background.exists():
            background = Path(__file__).parent / 'assets' / 'cosmic-background.png'
        if background.exists():
            self.background_source = tk.PhotoImage(file=str(background))
            self.background_pixels = self.canvas.tk.call(str(self.background_source), 'data', '-format', 'ppm')
            self.background = tk.PhotoImage(data=resized_ppm(self.background_pixels, self.card_width, self.card_height), format='PPM')
            self.background_item = self.canvas.create_image(0, 0, image=self.background, anchor='nw')
        self.canvas.create_rectangle(1, 1, 478, 318, outline='#345675', width=1)
        if hasattr(self, 'icon'):
            self.canvas.create_image(28, 26, image=self.header_icon)
        self.canvas.create_text(46, 25, text='C O D E X', fill=WHITE,
                                font=('Segoe UI', -19, 'bold'), anchor='w')
        self.canvas.create_text(23, 51, text='A LITTLE SPACE FOR YOUR LIMITS', fill=MUTED,
                                font=('Segoe UI', -9), anchor='w')
        self.state_label = CanvasLabel(self.canvas, 23, 251, 'Connecting', font=('Segoe UI', -10))
        self.updated_label = CanvasLabel(self.canvas, 456, 251, 'Refreshes every 5 min',
                                          anchor='e', font=('Segoe UI', -9))
        self.detail_label = CanvasLabel(self.canvas, 23, 232, '', width=430, font=('Segoe UI', -10))
        self.canvas.create_line(23, 268, 456, 268, fill='#263b55')
        self.canvas.create_text(456, 298, text='KRĒˈĀDIV WORX  ·  COSMIC', fill=MUTED,
                                font=('Segoe UI', -9), anchor='e')
        self.close_button = self.button(self.canvas, '×', self.close)
        self.close_button.place(x=442, y=14, width=24, height=24)
        self.refresh_button = self.button(self.canvas, '↻  Refresh', self.refresh)
        self.refresh_button.place(x=19, y=281, width=83, height=28)
        self.pin_button = tk.Checkbutton(self.canvas, text='Pin', variable=self.topmost,
            command=self.toggle_topmost, font=('Segoe UI', -11), bg=BG, fg=MUTED,
            activebackground='#14233a', activeforeground=WHITE, selectcolor='#14233a',
            indicatoron=False, bd=0, highlightthickness=1, highlightbackground=BG,
            highlightcolor=BLUE, cursor='hand2', takefocus=True)
        self.pin_button.place(x=111, y=281, width=56, height=28)
        self.menu_button = self.button(self.canvas, 'Menu', self.open_menu)
        self.menu_button.place(x=176, y=281, width=56, height=28)
        self.bind_drag(self.canvas)
        self.resize_grip = tk.Label(self.canvas, text='◢', font=('Segoe UI', -15),
                                    fg=BLUE, bg=BG, bd=0, cursor='size_nw_se')
        self.resize_grip.bind('<ButtonPress-1>', self.start_resize)
        self.resize_grip.bind('<B1-Motion>', self.drag_resize)
        self.resize_grip.bind('<ButtonRelease-1>', self.finish_resize)
        size_menu = tk.Menu(self.menu, tearoff=0)
        for label, width in [('Small',360), ('Default',480), ('Large',720)]:
            size_menu.add_command(label=label, command=lambda value=width: self.set_size(value))
        self.menu.insert_cascade(0, label='Size', menu=size_menu)
        self.startup = Startup()
        self.startup_enabled = tk.BooleanVar(value=self.startup.enabled())
        self.menu.insert_checkbutton(1, label='Launch at Windows sign-in', variable=self.startup_enabled,
                                    command=self.toggle_startup, state='disabled' if qa_frame else 'normal')
        self.ready = True
        self.auto_start = auto_start
        self.status_path = status_path
        self.layout_content()
        self.update_pin_text()
        self.paint_usage()
        self.position_controls()
        self.clamp_position()
        root.bind('<Control-p>', lambda event: self.keyboard_pin())
        root.bind('<Control-m>', lambda event: self.open_menu())
        root.bind('<Control-equal>', lambda event: self.set_size(self.card_width+60))
        root.bind('<Control-minus>', lambda event: self.set_size(self.card_width-60))
        self.closed_callbacks = []
        if auto_start:
            root.after(150, self.refresh)

    @staticmethod
    def button(parent, text, command):
        return tk.Button(parent, text=text, command=command, font=('Segoe UI', -11),
            bg=BG, fg=MUTED, activebackground='#14233a', activeforeground=WHITE,
            disabledforeground='#617187', bd=0, padx=0, pady=0, cursor='hand2',
            takefocus=True, highlightthickness=1, highlightbackground=BG, highlightcolor=BLUE)

    def keyboard_pin(self):
        self.topmost.set(not self.topmost.get())
        self.toggle_topmost()

    def style_window(self):
        if not self.qa_frame:
            super().style_window()

    def layout_content(self):
        if not self.ready:
            return super().layout_content()
        self.root.geometry(f'{self.card_width}x{self.card_height}')

    def position_controls(self):
        scale = self.card_width/480
        for button, x, y, width, height in [(self.close_button,442,14,24,24),
            (self.refresh_button,19,281,83,28),(self.pin_button,111,281,56,28),
            (self.menu_button,176,281,56,28)]:
            button.place(x=round(x*scale), y=round(y*scale), width=round(width*scale), height=round(height*scale))
            button.configure(font=('Segoe UI', -max(9,round(11*scale))))
        self.resize_grip.place(x=self.card_width-19,y=self.card_height-19,width=17,height=17)

    def scale_items(self):
        scale = self.card_width/480
        visible = set(self.canvas.find_all())
        self.base_items = {key:value for key,value in self.base_items.items() if key in visible}
        for item in visible:
            kind = self.canvas.type(item)
            if item not in self.base_items:
                font = self.canvas.tk.splitlist(self.canvas.itemcget(item,'font')) if kind == 'text' else None
                self.base_items[item] = (self.canvas.coords(item),font,self.canvas.itemcget(item,'width') if kind in ('text','line','rectangle') else None)
            coords, font, width = self.base_items[item]
            self.canvas.coords(item,*(n*scale for n in coords))
            if font:
                self.canvas.itemconfigure(item,font=(font[0],-max(7,round(abs(int(font[1]))*scale)),*font[2:]))
            if width:
                self.canvas.itemconfigure(item,width=float(width)*scale)
        self.scale = scale

    def set_size(self, width, save=True):
        self.card_width,self.card_height = card_size(width,self.root.winfo_screenwidth(),self.root.winfo_screenheight())
        self.root.geometry(f'{self.card_width}x{self.card_height}')
        self.position_controls()
        self.paint_usage()
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self.update_background)
        self.clamp_position()
        if save:
            self.persist()

    def update_background(self):
        self.resize_job = None
        if hasattr(self,'background_pixels'):
            self.background = tk.PhotoImage(data=resized_ppm(self.background_pixels,self.card_width,self.card_height),format='PPM')
            self.canvas.itemconfigure(self.background_item,image=self.background)
        self.write_status()

    def clamp_position(self):
        self.root.update_idletasks()
        x = max(0,min(self.root.winfo_x(),self.root.winfo_screenwidth()-self.card_width))
        y = max(0,min(self.root.winfo_y(),self.root.winfo_screenheight()-self.card_height))
        self.root.geometry(f'+{x}+{y}')

    def start_resize(self,event):
        self.resize_origin = (event.x_root,event.y_root,self.card_width)

    def drag_resize(self,event):
        if self.resize_origin:
            x,y,width = self.resize_origin
            horizontal,vertical = event.x_root-x,(event.y_root-y)*1.5
            delta = horizontal if abs(horizontal)>=abs(vertical) else vertical
            self.set_size(width+delta,save=False)

    def finish_resize(self,event):
        self.resize_origin = None
        self.persist()

    def persist(self):
        core.save_preferences(self.settings_path,{'x':self.root.winfo_x(),'y':self.root.winfo_y(),
            'topmost':self.topmost.get(),'width':self.card_width})

    def toggle_startup(self):
        try:
            if self.startup_enabled.get():
                self.startup.enable()
            else:
                self.startup.disable()
        except OSError as error:
            core.messagebox.showerror('Startup setting',str(error),parent=self.root)
        self.startup_enabled.set(self.startup.enabled())

    def render_countdown(self):
        if not self.ready:
            return super().render_countdown()
        if not self.failed:
            expired = any(w.reset is not None and w.reset <= time.time() for w in self.windows)
            self.state_label.config(text='Refreshing' if self.busy else
                ('Awaiting update' if expired else ('Updated' if self.windows else 'Connecting')),
                fg=MUTED if expired or not self.windows else BLUE)
        self.paint_usage()

    def draw_bar(self):
        if self.ready:
            self.paint_usage()
        else:
            super().draw_bar()

    def paint_usage(self):
        c = self.canvas
        c.delete('usage')
        self.layout_boxes = []
        def text(x, y, content, size=11, color=MUTED, bold=False, anchor='w', width=0):
            item = c.create_text(x, y, text=content, fill=color, anchor=anchor, width=width,
                font=('Segoe UI', -size, 'bold' if bold else 'normal'), tags='usage')
            self.layout_boxes.append(c.bbox(item))
            return item
        windows = self.display_windows()[:2]
        if not windows:
            c.create_rectangle(23, 72, 456, 222, outline='#29405d', tags='usage')
            text(40, 96, 'PLAN REMAINING', 10)
            text(40, 148, '—', 60, WHITE, True)
            text(285, 120, 'WAITING FOR CODEX', 10)
            text(285, 143, 'Usage unavailable' if self.failed else 'Reading your limits…', 11, WHITE)
        for index, w in enumerate(windows):
            double = len(windows) == 2
            top = 72 + index * 78
            bottom = top + (72 if double else 150)
            c.create_rectangle(23, top, 456, bottom, outline='#29405d', tags='usage')
            label = 'WEEKLY' if w.minutes == 10080 else w.label.upper()
            text(40, top+17, label + ' REMAINING', 10)
            number_y = top + (43 if double else 74)
            text(39, number_y, core.percentage(w.remaining), 37 if double else 64, WHITE, True)
            reset_x = 284
            c.create_line(265, top+15, 265, bottom-15, fill='#29405d', tags='usage')
            text(reset_x, top+18, 'NEXT RESET · LOCAL', 9)
            date = datetime.fromtimestamp(w.reset).strftime('%d %b · %H:%M') if w.reset else 'Unavailable'
            text(reset_x, top+(39 if double else 57), date, 14 if double else 18, WHITE, True)
            countdown = core.countdown(w.reset).replace('Resets in ', 'In ')
            text(reset_x, top+(59 if double else 83), countdown, 9 if double else 11, width=158)
            if not double:
                text(40, top+111, 'OF YOUR PLAN WINDOW', 9)
                c.create_line(41, bottom-17, 438, bottom-17, fill='#253b55', width=3, tags='usage')
                if w.remaining > 0:
                    c.create_line(41, bottom-17, 41+397*w.remaining/100, bottom-17,
                        fill=core.CORAL if w.remaining <= 15 else BLUE, width=3, tags='usage')
        # Permanent status and controls remain above the usage layer.
        if not self.failed:
            self.detail_label.config(text='')
        self.scale_items()

    def write_status(self):
        if self.status_path:
            self.root.update_idletasks()
            self.style_window()
            clipped = any((box:=self.canvas.bbox(item)) and
                (box[0]<0 or box[1]<0 or box[2]>self.card_width or box[3]>self.card_height)
                for item in self.canvas.find_all() if self.canvas.type(item)=='text')
            core.save_preferences(self.status_path, {'version': VERSION,
                'remaining': [w.remaining for w in self.display_windows()],
                'state': self.state_label.cget('text'), 'error': self.failed,
                'width': self.root.winfo_width(), 'height': self.root.winfo_height(),
                'text_clipped': clipped, 'rounded': self.rounding_applied})

    def about(self):
        core.messagebox.showinfo('Usage Card — Cosmic',
            f'{VERSION} · 7 October 2026\nA Krēˈādiv Worx public beta.\n'
            'Direction: Raiden. Implementation: Codi.\n\n'
            'Drag to move. Ctrl+R refreshes, Ctrl+P pins, Ctrl+M opens Menu. Escape closes.\n'
            'Drag the lower-right grip to resize. Menu includes sizes and Windows startup.\n'
            'Uses the installed Codex CLI sign-in; refreshes every five minutes.\n'
            'Remaining plan percentages, not credit balances. Local reset times.\n'
            'Independent of OpenAI. No model calls, analytics or reset redemption.', parent=self.root)


def smoke():
    with tempfile.TemporaryDirectory() as directory:
        root = tk.Tk()
        root.withdraw()
        card = CosmicWidget(root, Path(directory)/'settings.json', Path(directory)/'status.json', False)
        cases = [([core.Window(99,10080,int(time.time())+460800)], None),
            ([core.Window(72,300,int(time.time())+7200),core.Window(22,10080,None)], None),
            (None, 'Refresh timed out. Try again when online.'),
            ([core.Window(0,10080,int(time.time())-1)], None)]
        for windows, error in cases:
            card.apply_result(windows,error)
            assert not json.loads(card.status_path.read_text())['text_clipped']
        card.keyboard_pin()
        assert core.load_preferences(card.settings_path)['topmost'] is True
        card.apply_result(None, 'Offline test')
        assert card.state_label.cget('text') == 'Stale'
        assert card.windows[0].remaining == 0
        for width in (360,480,720,960):
            card.set_size(width)
            card.update_background()
            root.update_idletasks()
            card.write_status()
            assert not json.loads(card.status_path.read_text())['text_clipped'], width
            assert core.load_preferences(card.settings_path)['topmost'] is True
            assert read_size(card.settings_path)[0] == width
        card.apply_result([core.Window(100,300,None),core.Window(0,10080,int(time.time())-1)],None)
        for width in (360,720):
            card.set_size(width)
            root.update_idletasks()
            card.write_status()
            assert not json.loads(card.status_path.read_text())['text_clipped'], width
        card.close()
    print(json.dumps({'version': VERSION, 'native_cosmic_smoke': 'passed',
                      'cases': 'one/two/missing reset/zero/expired/stale/pin'}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--status-file', type=Path)
    parser.add_argument('--qa-window', action='store_true', help='Framed, isolated window for native visual QA')
    parser.add_argument('--enable-startup',action='store_true')
    parser.add_argument('--disable-startup',action='store_true')
    args = parser.parse_args()
    if args.enable_startup or args.disable_startup:
        startup = Startup()
        startup.enable() if args.enable_startup else startup.disable()
        print(json.dumps({'startup_enabled':startup.enabled()}))
        return
    if args.smoke:
        smoke()
        return
    mutex = None
    if os.name == 'nt':
        ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False,
            'Local\\KreadivCodexCosmicQA' if args.qa_window else 'Local\\KreadivCodexCosmicPreview')
        if ctypes.windll.kernel32.GetLastError() == 183:
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError,OSError):
            pass
    try:
        root = tk.Tk()
        settings = settings_file()
        previous = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'kreadiv-worx' / 'CodexUsageCosmic' / 'settings.json'
        if not args.qa_window and previous != settings and not settings.exists() and previous.is_file():
            old = core.load_preferences(previous)
            old['width'] = read_size(previous)[0]
            core.save_preferences(settings,old)
        if args.qa_window:
            settings = Path(tempfile.gettempdir()) / 'kreadiv-cosmic-qa-settings.json'
        card = CosmicWidget(root,settings,args.status_file,qa_frame=args.qa_window)
        if args.qa_window:
            root.overrideredirect(False)
            root.title('Cosmic visual QA')
            root.geometry(f'{card.card_width}x{card.card_height}+100+100')
        root.mainloop()
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == '__main__':
    main()

