import tkinter as tk
from tkinter import ttk
import serial
from serial.tools import list_ports


class RobotControl(tk.Tk):
    BAUD = 115200
    HEARTBEAT_MS = 100
    DIRECTIONS = {
        'forward': (1, 1),
        'backward': (-1, -1),
        'left': (-1, 1),
        'right': (1, -1),
    }

    def __init__(self):
        super().__init__()
        self.title('Robot Control')
        self.geometry('520x530')
        self.minsize(460, 500)
        self.configure(bg='#111827')
        self.connection = None
        self.ready = False
        self.motion = None
        self.connect_job = None
        self.heartbeat_job = None
        self.speed = tk.IntVar(value=0)
        self.port = tk.StringVar()
        self.status = tk.StringVar(value='Déconnecté')
        self.motion_text = tk.StringVar(value='À l’arrêt')
        self.speed_text = tk.StringVar(value='0 / 255')
        self.buttons = {}
        self.build_ui()
        self.refresh_ports()
        self.bind('<ButtonRelease-1>', self.stop)
        self.bind('<Escape>', self.stop)
        self.bind('<FocusOut>', self.on_focus_out)
        self.bind('<Unmap>', self.on_unmap)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.heartbeat()

    def build_ui(self):
        bg, panel, fg, muted = '#111827', '#1f2937', '#f9fafb', '#aeb9c9'
        self.option_add('*Font', ('Segoe UI', 11))
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', padding=6)
        style.configure('TButton', padding=7)

        tk.Label(self, text='ROBOT CONTROL', bg=bg, fg=fg,
                 font=('Segoe UI', 24, 'bold')).pack(pady=(22, 2))
        tk.Label(self, text='Commande différentielle • Arduino', bg=bg,
                 fg=muted).pack(pady=(0, 15))

        connection = tk.Frame(self, bg=bg)
        connection.pack(fill='x', padx=25)
        self.ports = ttk.Combobox(connection, textvariable=self.port,
                                  state='readonly', width=12)
        self.ports.pack(side='left', fill='x', expand=True)
        ttk.Button(connection, text='Actualiser', command=self.refresh_ports).pack(side='left', padx=6)
        self.connect_button = ttk.Button(connection, text='Connecter', command=self.toggle_connection)
        self.connect_button.pack(side='left')
        tk.Label(self, textvariable=self.status, bg=bg, fg=muted).pack(pady=(7, 10))

        speed_panel = tk.Frame(self, bg=panel, padx=18, pady=10)
        speed_panel.pack(fill='x', padx=25)
        tk.Label(speed_panel, text='VITESSE / PWM', bg=panel, fg=muted,
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        tk.Label(speed_panel, textvariable=self.speed_text, bg=panel, fg=fg,
                 font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        tk.Scale(speed_panel, from_=0, to=255, orient='horizontal',
                 variable=self.speed, command=self.on_speed, showvalue=False,
                 bg=panel, fg=fg, troughcolor='#374151', highlightthickness=0,
                 activebackground='#60a5fa', sliderrelief='flat').pack(fill='x')

        controls = tk.Frame(self, bg=bg)
        controls.pack(pady=(17, 6))
        for direction, label, row, col in (
            ('forward', '↑  Avancer', 0, 1),
            ('left', '←  Gauche', 1, 0),
            ('right', 'Droite  →', 1, 2),
            ('backward', '↓  Reculer', 2, 1),
        ):
            button = tk.Button(controls, text=label, width=12, height=2,
                               bg='#374151', fg=fg, activebackground='#2563eb',
                               activeforeground='white', disabledforeground='#778398',
                               relief='flat', bd=0, state='disabled', takefocus=False)
            button.grid(row=row, column=col, padx=4, pady=4)
            button.bind('<ButtonPress-1>', lambda e, d=direction: self.start(d))
            button.bind('<Leave>', lambda e, d=direction: self.leave_direction(d))
            self.buttons[direction] = button
        tk.Button(controls, text='STOP', command=self.stop, width=12, height=2,
                  bg='#51252b', fg='#fca5a5', activebackground='#991b1b',
                  activeforeground='white', relief='flat', bd=0).grid(row=1, column=1, padx=4, pady=4)
        tk.Label(self, textvariable=self.motion_text, bg=bg, fg='#93c5fd',
                 font=('Segoe UI', 11, 'bold')).pack()
        tk.Label(self, text='Maintenir pour rouler • Relâcher ou Échap pour arrêter',
                 bg=bg, fg=muted, font=('Segoe UI', 9)).pack(pady=(4, 12))

    def refresh_ports(self):
        devices = [p.device for p in list_ports.comports()]
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
        self.connect_button.configure(text='Déconnecter')
        self.ports.configure(state='disabled')
        # L'ouverture du port peut redémarrer un Arduino Uno.
        self.connect_job = self.after(2000, self.finish_connection)

    def finish_connection(self):
        self.connect_job = None
        if self.connection is None:
            return
        self.ready = True
        if self.send(0, 0):
            self.status.set(f'Port ouvert : {self.connection.port}')
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
            return
        self.motion = direction
        self.buttons[direction].configure(bg='#2563eb')
        self.motion_text.set(self.buttons[direction]['text'])
        self.send_motion()
        return 'break'

    def stop(self, event=None):
        self.motion = None
        self.motion_text.set('À l’arrêt')
        for button in self.buttons.values():
            button.configure(bg='#374151')
        if self.ready:
            self.send(0, 0)

    def leave_direction(self, direction):
        if self.motion == direction:
            self.stop()

    def on_speed(self, value):
        self.speed_text.set(f'{int(float(value))} / 255')
        if self.motion is not None:
            self.send_motion()

    def on_focus_out(self, event):
        self.after_idle(self.check_focus)

    def check_focus(self):
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
        self.connect_button.configure(text='Connecter')
        self.status.set('Déconnecté')

    def close(self):
        if self.heartbeat_job is not None:
            self.after_cancel(self.heartbeat_job)
        self.disconnect()
        self.destroy()


if __name__ == '__main__':
    RobotControl().mainloop()
