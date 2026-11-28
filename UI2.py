import tkinter as tk
from tkinter import ttk
import serial
from serial.tools import list_ports


class RobotControl(tk.Tk):
    BAUD = 115200
    HEARTBEAT_MS = 100
    DIRECTIONS = {'forward': (1, 1), 'backward': (-1, -1),
                  'left': (-1, 1), 'right': (1, -1)}
    LABELS = {'forward': 'Marche avant', 'backward': 'Marche arrière',
              'left': 'Rotation gauche', 'right': 'Rotation droite'}

    BG = '#0b1120'
    PANEL = '#131d2f'
    TILE = '#1c293e'
    BORDER = '#27364d'
    FG = '#e9f0fb'
    MUTED = '#8b9db8'
    CYAN = '#55e4d0'
    RED = '#ff7b88'
    BLUE = '#264d70'
    FONT = 'Segoe UI'

    def __init__(self):
        super().__init__()
        self.title('DRIVE / Robot Control Studio')
        self.geometry('950x620')
        self.minsize(820, 580)
        self.configure(bg=self.BG)
        self.connection = None
        self.ready = False
        self.motion = None
        self.connect_job = None
        self.heartbeat_job = None
        self.focus_job = None
        self.speed = tk.IntVar(value=0)
        self.port = tk.StringVar()
        self.status = tk.StringVar(value='Déconnecté')
        self.motion_text = tk.StringVar(value='À l’arrêt')
        self.buttons = {}
        self.build_ui()
        self.refresh_ports()
        self.bind('<ButtonRelease-1>', self.stop)
        self.bind('<Escape>', self.stop)
        self.bind('<FocusOut>', self.on_focus_out)
        self.bind('<Unmap>', self.on_unmap)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.heartbeat()

    def label(self, parent, text='', size=11, color=None, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget('bg'),
                        fg=color or self.FG,
                        font=(self.FONT, size, 'bold' if bold else 'normal'),
                        **kwargs)

    def button(self, parent, text, command=None, bg=None, fg=None, **kwargs):
        return tk.Button(parent, text=text, command=command,
                         bg=bg or self.TILE, fg=fg or self.FG,
                         activebackground=self.BLUE, activeforeground=self.FG,
                         disabledforeground=self.MUTED, relief='flat', bd=0,
                         font=(self.FONT, 11, 'bold'), cursor='hand2', **kwargs)

    def panel(self, parent):
        return tk.Frame(parent, bg=self.PANEL, highlightbackground=self.BORDER,
                        highlightthickness=1, padx=20, pady=16)

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Drive.TCombobox', fieldbackground=self.TILE,
                        background=self.TILE, foreground=self.FG,
                        arrowcolor=self.CYAN, bordercolor=self.BORDER,
                        lightcolor=self.BORDER, darkcolor=self.BORDER, padding=7,
                        font=(self.FONT, 11))
        style.map('Drive.TCombobox', fieldbackground=[('readonly', self.TILE),
                  ('disabled', self.TILE)], foreground=[('readonly', self.FG),
                  ('disabled', self.MUTED)], selectbackground=[('readonly', self.TILE)],
                  selectforeground=[('readonly', self.FG)])
        self.option_add('*TCombobox*Listbox.background', self.TILE)
        self.option_add('*TCombobox*Listbox.foreground', self.FG)
        self.option_add('*TCombobox*Listbox.selectBackground', self.BLUE)

        header = tk.Frame(self, bg=self.BG)
        header.pack(fill='x', padx=26, pady=(18, 14))
        identity = tk.Frame(header, bg=self.BG)
        identity.pack(side='left')
        self.label(identity, 'D R I V E  /  0 1', 10, self.CYAN, True).pack(anchor='w')
        self.label(identity, 'Robot Control Studio', 25, bold=True).pack(anchor='w')
        self.label(identity, 'Console de pilotage différentiel', 10, self.MUTED).pack(anchor='w')
        badge = tk.Frame(header, bg=self.PANEL, padx=13, pady=9)
        badge.pack(side='right', anchor='n', pady=7)
        self.status_dot = tk.Canvas(badge, width=12, height=12, bg=self.PANEL, highlightthickness=0)
        self.status_dot.pack(side='left', padx=(0, 8))
        self.dot = self.status_dot.create_oval(2, 2, 10, 10, fill=self.RED, outline='')
        self.connection_badge = self.label(badge, 'HORS LIGNE', 10, self.MUTED, True)
        self.connection_badge.pack(side='left')

        connection = self.panel(self)
        connection.pack(fill='x', padx=26, pady=(0, 14))
        self.label(connection, '01  /  LIAISON SÉRIE', 10, self.CYAN, True).pack(side='left', padx=(0, 16))
        self.ports = ttk.Combobox(connection, textvariable=self.port, state='readonly',
                                  width=10, style='Drive.TCombobox')
        self.ports.pack(side='left')
        self.button(connection, 'Actualiser', self.refresh_ports, padx=12, pady=6).pack(side='left', padx=7)
        self.connect_button = self.button(connection, 'Connecter', self.toggle_connection,
                                          bg=self.CYAN, fg=self.BG, padx=15, pady=6)
        self.connect_button.pack(side='left')
        self.label(connection, '115200 bauds', 10, self.MUTED).pack(side='right')

        main = tk.Frame(self, bg=self.BG)
        main.pack(fill='both', expand=True, padx=26)
        main.columnconfigure(0, weight=4, uniform='main')
        main.columnconfigure(1, weight=5, uniform='main')
        main.rowconfigure(0, weight=1)

        speed_panel = self.panel(main)
        speed_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 7))
        self.label(speed_panel, '02  /  PUISSANCE', 10, self.CYAN, True).pack(anchor='w')
        self.gauge = tk.Canvas(speed_panel, bg=self.PANEL, highlightthickness=0, height=170)
        self.gauge.pack(fill='both', expand=True, pady=(6, 0))
        self.gauge.bind('<Configure>', lambda event: self.draw_gauge())
        tk.Scale(speed_panel, from_=0, to=255, resolution=1, orient='horizontal',
                 variable=self.speed, command=self.on_speed, showvalue=False,
                 bg=self.PANEL, fg=self.FG, troughcolor=self.BORDER,
                 highlightthickness=0, activebackground=self.CYAN,
                 sliderrelief='flat', sliderlength=20, width=15, bd=0).pack(fill='x')
        ticks = tk.Frame(speed_panel, bg=self.PANEL)
        ticks.pack(fill='x')
        self.label(ticks, '0', 9, self.MUTED).pack(side='left')
        self.label(ticks, '255', 9, self.MUTED).pack(side='right')
        presets = tk.Frame(speed_panel, bg=self.PANEL)
        presets.pack(fill='x', pady=(12, 0))
        for value, name in [(64, '25 %'), (128, '50 %'), (191, '75 %'), (255, '100 %')]:
            self.button(presets, name, lambda v=value: self.set_speed(v), pady=5).pack(side='left', fill='x', expand=True, padx=2)

        control = self.panel(main)
        control.grid(row=0, column=1, sticky='nsew', padx=(7, 0))
        self.label(control, '03  /  NAVIGATION', 10, self.CYAN, True).pack(anchor='w')
        self.label(control, textvariable=self.motion_text, size=20, bold=True).pack(anchor='w', pady=(5, 2))
        pad = tk.Frame(control, bg=self.PANEL)
        pad.pack(expand=True, pady=8)
        for direction, label, r, c in (
                ('forward', '↑\nAVANCER', 0, 1), ('left', '←\nGAUCHE', 1, 0),
                ('right', '→\nDROITE', 1, 2), ('backward', '↓\nRECULER', 2, 1)):
            b = self.button(pad, label, width=10, height=2, state='disabled', takefocus=False)
            b.grid(row=r, column=c, padx=4, pady=4, sticky='nsew')
            b.bind('<ButtonPress-1>', lambda e, d=direction: self.start(d))
            b.bind('<Leave>', lambda e, d=direction: self.leave_direction(d))
            self.buttons[direction] = b
        self.button(pad, '■\nSTOP', self.stop, bg='#482532', fg=self.RED,
                    width=10, height=2, takefocus=False).grid(row=1, column=1, padx=4, pady=4)
        self.label(control, 'Maintenir pour avancer • Relâcher / Échap pour arrêter', 9,
                   self.MUTED, wraplength=340, justify='center').pack(pady=(4, 0))

        bottom = tk.Frame(self, bg=self.BG)
        bottom.pack(fill='x', padx=26, pady=(14, 0))
        bottom.columnconfigure((0, 1), weight=1, uniform='motors')
        self.motor_labels = {}
        self.motor_bars = {}
        for i, (key, name) in enumerate([('left', 'MOTEUR GAUCHE'), ('right', 'MOTEUR DROIT')]):
            motor = tk.Frame(bottom, bg=self.PANEL, padx=15, pady=9,
                             highlightthickness=1, highlightbackground=self.BORDER)
            motor.grid(row=0, column=i, sticky='ew', padx=(0, 7) if i == 0 else (7, 0))
            top = tk.Frame(motor, bg=self.PANEL)
            top.pack(fill='x')
            self.label(top, name, 9, self.MUTED, True).pack(side='left')
            value = self.label(top, '0 PWM', 12, self.FG, True)
            value.pack(side='right')
            bar = tk.Canvas(motor, bg=self.PANEL, height=9, highlightthickness=0)
            bar.pack(fill='x', pady=(5, 0))
            bar.bind('<Configure>', lambda e: self.update_motors())
            self.motor_labels[key] = value
            self.motor_bars[key] = bar
        footer = tk.Frame(self, bg=self.BG)
        footer.pack(fill='x', padx=26, pady=(8, 12))
        self.label(footer, textvariable=self.status, size=9, color=self.MUTED,
                   anchor='w', wraplength=630, justify='left').pack(side='left', fill='x', expand=True)
        self.label(footer, 'ARDUINO  /  PWM CMD', 9, self.MUTED, True).pack(side='right')

    def draw_gauge(self):
        c = self.gauge
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        if w < 40 or h < 40:
            return
        pwm = self.speed.get()
        r = min((w - 30) / 2, (h - 18) / 1.8, 106)
        x, y = w / 2, h / 2 + r * 0.12
        bounds = (x-r, y-r, x+r, y+r)
        c.create_arc(*bounds, start=225, extent=-270, style='arc', width=12, outline=self.BORDER)
        if pwm:
            c.create_arc(*bounds, start=225, extent=-270*pwm/255,
                         style='arc', width=12, outline=self.CYAN)
        # A full circle is intentionally avoided: the gauge is a 270-degree arc.
        c.create_text(x, y-10, text=str(pwm), font=(self.FONT, 38, 'bold'), fill=self.FG)
        c.create_text(x, y+25, text=f'{pwm / 255:.0%}  ·  PWM', font=(self.FONT, 10, 'bold'), fill=self.MUTED)

    def update_motors(self):
        factors = self.DIRECTIONS.get(self.motion, (0, 0)) if self.ready else (0, 0)
        for key, factor in zip(('left', 'right'), factors):
            if key not in self.motor_bars:
                continue
            value = factor * self.speed.get()
            self.motor_labels[key].configure(text=f'{value:+d} PWM' if value else '0 PWM',
                                             fg=self.CYAN if value > 0 else self.RED if value < 0 else self.FG)
            bar = self.motor_bars[key]
            bar.delete('all')
            w = bar.winfo_width()
            mid = w / 2
            bar.create_rectangle(0, 2, w, 7, fill=self.BORDER, outline='')
            end = mid + (mid - 1) * value / 255
            if value:
                bar.create_rectangle(min(mid, end), 2, max(mid, end), 7,
                                     fill=self.CYAN if value > 0 else self.RED, outline='')
            bar.create_line(mid, 0, mid, 9, fill=self.MUTED)

    def set_speed(self, value):
        self.speed.set(value)
        self.on_speed(value)

    def on_speed(self, value):
        self.draw_gauge()
        self.update_motors()
        if self.motion is not None:
            self.send_motion()

    def set_connection_status(self, text, color):
        self.status_dot.itemconfigure(self.dot, fill=color)
        self.connection_badge.configure(text=text, fg=color)

    def refresh_ports(self):
        if self.connection is not None:
            return
        try:
            devices = [p.device for p in list_ports.comports()]
        except (serial.SerialException, OSError):
            self.status.set('Impossible de détecter les ports série')
            return
        self.ports['values'] = devices
        if self.port.get() not in devices:
            self.port.set(devices[0] if devices else '')

    def toggle_connection(self):
        if self.connection is not None:
            self.disconnect()
            return
        if not self.port.get():
            self.status.set('Aucun port série sélectionné')
            return
        try:
            self.connection = serial.Serial(self.port.get(), self.BAUD,
                                            timeout=0, write_timeout=0.1)
        except (serial.SerialException, OSError) as exc:
            self.status.set(f'Connexion impossible : {exc}')
            return
        self.status.set('Initialisation de l’Arduino…')
        self.set_connection_status('INITIALISATION', '#f6bd69')
        self.connect_button.configure(text='Déconnecter', bg=self.TILE, fg=self.FG)
        self.ports.configure(state='disabled')
        self.connect_job = self.after(2000, self.finish_connection)

    def finish_connection(self):
        self.connect_job = None
        if self.connection is None:
            return
        self.ready = True
        if self.send(0, 0):
            self.status.set(f'Port ouvert : {self.connection.port}')
            self.set_connection_status('PORT OUVERT', self.CYAN)
            for button in self.buttons.values():
                button.configure(state='normal')

    def send(self, left, right):
        if not self.ready or self.connection is None:
            return False
        try:
            packet = f'{left},{right}\n'.encode('ascii')
            if self.connection.write(packet) != len(packet):
                raise serial.SerialException('Transmission incomplète')
            return True
        except (serial.SerialException, OSError):
            self.disconnect(send_stop=False)
            self.status.set('Connexion série perdue')
            return False

    def control_bluetooth(self, left, right):
        pass

    def send_motion(self):
        left, right = self.DIRECTIONS.get(self.motion, (0, 0))
        pwm = self.speed.get()
        return self.send(left * pwm, right * pwm)

    def start(self, direction):
        if not self.ready:
            return 'break'
        self.motion = direction
        for key, button in self.buttons.items():
            button.configure(bg=self.BLUE if key == direction else self.TILE)
        self.motion_text.set(self.LABELS[direction])
        self.update_motors()
        self.send_motion()
        return 'break'

    def stop(self, event=None):
        self.motion = None
        self.motion_text.set('À l’arrêt')
        for button in self.buttons.values():
            button.configure(bg=self.TILE)
        self.update_motors()
        if self.ready:
            self.send(0, 0)

    def leave_direction(self, direction):
        if self.motion == direction:
            self.stop()

    def on_focus_out(self, event):
        if self.focus_job is None:
            self.focus_job = self.after_idle(self.check_focus)

    def check_focus(self):
        self.focus_job = None
        if self.focus_displayof() is None:
            self.stop()

    def on_unmap(self, event):
        if event.widget is self:
            self.stop()

    def heartbeat(self):
        if self.ready:
            self.send_motion()
        self.heartbeat_job = self.after(self.HEARTBEAT_MS, self.heartbeat)

    def disconnect(self, send_stop=True):
        if self.connect_job is not None:
            self.after_cancel(self.connect_job)
            self.connect_job = None
        if self.connection is not None:
            if send_stop:
                try:
                    self.connection.write(b'0,0\n')
                except (serial.SerialException, OSError):
                    pass
            try:
                self.connection.close()
            except (serial.SerialException, OSError):
                pass
        self.connection = None
        self.ready = False
        self.stop()
        for button in self.buttons.values():
            button.configure(state='disabled')
        self.ports.configure(state='readonly')
        self.connect_button.configure(text='Connecter', bg=self.CYAN, fg=self.BG)
        self.set_connection_status('HORS LIGNE', self.RED)
        self.status.set('Déconnecté')

    def close(self):
        for job in (self.heartbeat_job, self.focus_job):
            if job is not None:
                self.after_cancel(job)
        self.disconnect()
        self.destroy()


if __name__ == '__main__':
    RobotControl().mainloop()
