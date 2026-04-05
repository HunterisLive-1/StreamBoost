import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import json
import os
import threading
import time
from datetime import datetime
import sys
import ctypes
import glob
import shutil

# --- pystray / PIL handling ---
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ─── System processes jo KABHI kill nahi karne ───────────────────────────────
SYSTEM_PROTECTED = {
    'system', 'system idle process', 'registry', 'smss.exe', 'csrss.exe',
    'wininit.exe', 'services.exe', 'lsass.exe', 'dwm.exe', 'winlogon.exe',
    'fontdrvhost.exe', 'sihost.exe', 'taskhostw.exe', 'ctfmon.exe',
    'spoolsv.exe', 'dllhost.exe', 'conhost.exe', 'wudfhost.exe',
    'runtimebroker.exe', 'searchhost.exe', 'startmenuexperiencehost.exe',
    'textinputhost.exe', 'shellexperiencehost.exe', 'securityhealthsystray.exe',
    'securityhealthservice.exe', 'audiodg.exe', 'msdtc.exe', 'lsm.exe',
    'ntoskrnl.exe', 'hal.dll', 'streamboost.exe', 'python.exe', 'pythonw.exe',
    'explorer.exe', 'svchost.exe', 'taskmgr.exe'
}

STREAMER_DEFAULTS = {
    'obs64.exe', 'obs32.exe', 'obs.exe',
    'douwan.exe', 'chrome.exe', 'msedge.exe', 'firefox.exe',
    'discord.exe', 'audiodg.exe', 'steam.exe', 'vlc.exe', 'musicbee.exe',
    'spotify.exe'
}

CONFIG_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "streamboost_config.json")

# ─── Colors ───────────────────────────────────────────────────────────────────
BG_MAIN    = '#0a0e1a'      # Deep Navy Cyberpunk
BG_CARD    = '#12192a'      # Lighter Nav
BG_ROW1    = '#161b22'
BG_ROW2    = '#12192a'
BG_HEADER  = '#1f293d'
ACCENT     = '#00d4ff'      # Neon Cyan
MAGENTA    = '#ff2d78'      # Pink/Magenta for danger/kill
GREEN      = '#00ff88'      # Neon Green
RED        = '#ff2a2a'
YELLOW     = '#ffda00'
TEXT_MAIN  = '#e6edf3'
TEXT_DIM   = '#687b9e'
BTN_KILL   = '#da3633'
BTN_AUTO   = '#238636'
BTN_STOP   = '#b62324'

class StreamBoostEngine:
    def __init__(self):
        self.config = {
            'whitelist': list(STREAMER_DEFAULTS),
            'profiles': {
                'Stream Mode': list(STREAMER_DEFAULTS),
                'Gaming Mode': ['steam.exe', 'discord.exe', 'audiodg.exe'],
                'Aggressive': []
            },
            'active_profile': 'Stream Mode',
            'auto_kill_interval': 10,
            'minimize_to_tray': True
        }
        self.load_config()
        self.whitelist = set(self.config['whitelist'])

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except: pass

    def save_config(self):
        self.config['whitelist'] = list(self.whitelist)
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except: pass

    def get_processes(self):
        procs = []
        seen_names = {}
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                name = info['name']
                if not name or name.lower() in SYSTEM_PROTECTED: continue
                ram = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                cpu = info['cpu_percent'] or 0.0
                pid = info['pid']

                if name in seen_names:
                    seen_names[name]['ram'] += ram
                    seen_names[name]['instances'] += 1
                else:
                    seen_names[name] = {'name': name, 'pid': pid, 'cpu': cpu, 'ram': ram, 'instances': 1}
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return sorted(list(seen_names.values()), key=lambda x: x['ram'], reverse=True)

    def optimize_ram(self):
        # Empty working sets to flush RAM
        freed = 0
        try:
            # Using undocumented PSAPI function
            psapi = ctypes.WinDLL('psapi')
            kernel32 = ctypes.WinDLL('kernel32')
            pid_list = (ctypes.c_ulong * 1024)()
            cb_needed = ctypes.c_ulong()
            if psapi.EnumProcesses(ctypes.byref(pid_list), ctypes.sizeof(pid_list), ctypes.byref(cb_needed)):
                num_procs = int(cb_needed.value / ctypes.sizeof(ctypes.c_ulong))
                for i in range(num_procs):
                    pid = pid_list[i]
                    if pid == 0: continue
                    h_process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid) # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
                    if h_process:
                        psapi.EmptyWorkingSet(h_process)
                        kernel32.CloseHandle(h_process)
            freed = 1 # Indicator of success
        except Exception as e:
            print("RAM Optimize Error:", e)
        return freed

class StreamBoostUI:
    def __init__(self, root, engine):
        self.root = root
        self.engine = engine
        self.root.title("StreamBoost 2.0 ⚡")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        self.root.configure(bg=BG_MAIN)
        self.tray_icon = None

        if sys.platform == "win32":
            self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.auto_kill_active = False
        self.current_view = None
        self.views = {}

        self.setup_ui()
        self.switch_to('dashboard')
        self.start_monitoring()

    def hide_window(self):
        if self.engine.config.get('minimize_to_tray', True) and HAS_TRAY:
            self.root.withdraw()
            self.create_tray()
        else:
            self.root.destroy()
            os._exit(0)

    def show_window(self, icon, item):
        self.tray_icon.stop()
        self.root.after(0, self.root.deiconify)

    def exit_app(self, icon, item):
        self.tray_icon.stop()
        self.root.destroy()
        os._exit(0)

    def create_tray(self):
        if not HAS_TRAY: return
        image = Image.new('RGB', (64, 64), color = BG_MAIN)
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=ACCENT)
        
        menu = (item('Open StreamBoost', self.show_window), item('Exit', self.exit_app))
        self.tray_icon = pystray.Icon("StreamBoost", image, "StreamBoost ⚡", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def setup_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=BG_CARD, width=200)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Title in sidebar
        tk.Label(self.sidebar, text="⚡ StreamBoost", font=('Segoe UI', 16, 'bold'), bg=BG_CARD, fg=ACCENT).pack(pady=(20, 5))
        tk.Label(self.sidebar, text="By HunterisLive", font=('Segoe UI', 9, 'italic'), bg=BG_CARD, fg=TEXT_DIM).pack(pady=(0, 20))

        # Nav Buttons
        self.nav_btns = {}
        nav_items = [('dashboard', '📊 Dashboard'), ('processes', '⚙️ Processes'), 
                     ('cleanup', '🧹 Cleanup'), ('memory', '💾 RAM Opt'), 
                     ('profiles', '🎮 Profiles'), ('settings', '🔧 Settings')]
        
        for view_id, text in nav_items:
            btn = tk.Button(self.sidebar, text=text, font=('Segoe UI', 11, 'bold'), anchor='w', bg=BG_CARD, fg=TEXT_DIM,
                            activebackground=BG_HEADER, activeforeground=TEXT_MAIN, relief='flat', bd=0, padx=20,
                            command=lambda v=view_id: self.switch_to(v))
            btn.pack(fill='x', pady=2)
            self.nav_btns[view_id] = btn

        # Main Content Area
        self.main_content = tk.Frame(self.root, bg=BG_MAIN)
        self.main_content.pack(side='right', fill='both', expand=True)

        # Initialize Views
        self.views['dashboard'] = DashboardView(self.main_content, self.engine, self)
        self.views['processes'] = ProcessView(self.main_content, self.engine, self)
        self.views['cleanup'] = CleanupView(self.main_content, self.engine, self)
        self.views['memory'] = MemoryView(self.main_content, self.engine, self)
        self.views['profiles'] = ProfilesView(self.main_content, self.engine, self)
        self.views['settings'] = SettingsView(self.main_content, self.engine, self)

    def switch_to(self, view_id):
        if self.current_view:
            self.views[self.current_view].pack_forget()
            self.nav_btns[self.current_view].config(bg=BG_CARD, fg=TEXT_DIM)
        
        self.current_view = view_id
        self.views[view_id].pack(fill='both', expand=True)
        self.nav_btns[view_id].config(bg=BG_HEADER, fg=ACCENT)
        if hasattr(self.views[view_id], 'on_show'):
            self.views[view_id].on_show()

    def start_monitoring(self):
        def monitor():
            while True:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                if self.current_view == 'dashboard':
                    self.root.after(0, lambda: self.views['dashboard'].update_gauges(cpu, ram))
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()

# ─── VIEWS ───────────────────────────────────────────────────────────────────

class DashboardView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        self.app = app
        tk.Label(self, text="System Dashboard", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', padx=30, pady=20)
        
        # Gauges Frame
        self.gauge_frame = tk.Frame(self, bg=BG_MAIN)
        self.gauge_frame.pack(fill='x', padx=30, pady=10)

        self.cpu_var = tk.StringVar(value="CPU: --%")
        self.ram_var = tk.StringVar(value="RAM: --%")

        self._create_card(self.gauge_frame, "CPU Usage", self.cpu_var, ACCENT).pack(side='left', expand=True, fill='both', padx=10)
        self._create_card(self.gauge_frame, "RAM Usage", self.ram_var, MAGENTA).pack(side='right', expand=True, fill='both', padx=10)

        # Quick Actions
        qa_frame = tk.Frame(self, bg=BG_MAIN)
        qa_frame.pack(fill='x', padx=30, pady=30)
        tk.Label(qa_frame, text="Quick Actions", font=('Segoe UI', 14, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', pady=(0, 10))
        
        btn_frame = tk.Frame(qa_frame, bg=BG_MAIN)
        btn_frame.pack(fill='x')
        
        tk.Button(btn_frame, text="💀 Kill Unnecessary Processes Now", bg=MAGENTA, fg='white', font=('Segoe UI', 11, 'bold'), 
                  relief='flat', padx=15, pady=10, command=self.kill_now).pack(side='left', padx=(0, 10))
        tk.Button(btn_frame, text="🧹 Quick Temp Clean", bg=BG_HEADER, fg=ACCENT, font=('Segoe UI', 11, 'bold'), 
                  relief='flat', padx=15, pady=10, command=lambda: self.app.switch_to('cleanup')).pack(side='left')

    def _create_card(self, parent, title, var, color):
        f = tk.Frame(parent, bg=BG_CARD, padx=20, pady=20)
        tk.Label(f, text=title, bg=BG_CARD, fg=TEXT_DIM, font=('Segoe UI', 12)).pack(anchor='w')
        tk.Label(f, textvariable=var, bg=BG_CARD, fg=color, font=('Segoe UI', 24, 'bold')).pack(anchor='w', pady=(10, 0))
        return f

    def update_gauges(self, cpu, ram):
        self.cpu_var.set(f"CPU: {cpu}%")
        self.ram_var.set(f"RAM: {ram}%")

    def kill_now(self):
        self.app.views['processes'].do_kill_unmarked()
        messagebox.showinfo("StreamBoost", "Processes cleared successfully!")

class ProcessView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        self.app = app
        
        # Header
        hdr = tk.Frame(self, bg=BG_MAIN)
        hdr.pack(fill='x', padx=30, pady=20)
        tk.Label(hdr, text="Process Manager", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(side='left')
        
        tk.Button(hdr, text="🔄 Refresh", bg=BG_HEADER, fg=TEXT_MAIN, relief='flat', padx=10, command=self.on_show).pack(side='right', padx=5)
        self.auto_btn = tk.Button(hdr, text="▶ Auto-Kill OFF", bg=BTN_AUTO, fg='white', relief='flat', padx=10, command=self.toggle_auto)
        self.auto_btn.pack(side='right', padx=5)
        tk.Button(hdr, text="💀 Kill Unmarked", bg=MAGENTA, fg='white', relief='flat', padx=10, command=self.do_kill_unmarked).pack(side='right', padx=5)

        # Search
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self.render_list())
        search = tk.Entry(self, textvariable=self.search_var, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, relief='flat', font=('Segoe UI', 11))
        search.pack(fill='x', padx=30, ipady=5)
        search.insert(0, "Search processes...")
        search.bind('<FocusIn>', lambda e: search.delete(0, 'end') if search.get() == "Search processes..." else None)

        # List headers
        col_hdr = tk.Frame(self, bg=BG_HEADER, pady=5)
        col_hdr.pack(fill='x', padx=30, pady=(15, 0))
        tk.Label(col_hdr, text="KEEP", width=6, bg=BG_HEADER, fg=ACCENT, font=('Segoe UI', 9, 'bold')).pack(side='left')
        tk.Label(col_hdr, text="Process Name", bg=BG_HEADER, fg=ACCENT, font=('Segoe UI', 9, 'bold'), anchor='w').pack(side='left', padx=10)
        tk.Label(col_hdr, text="CPU%", width=8, bg=BG_HEADER, fg=ACCENT, font=('Segoe UI', 9, 'bold')).pack(side='right', padx=10)
        tk.Label(col_hdr, text="RAM (MB)", width=10, bg=BG_HEADER, fg=ACCENT, font=('Segoe UI', 9, 'bold')).pack(side='right')

        # Scrollable list
        self.canvas = tk.Canvas(self, bg=BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG_MAIN)
        self.scroll_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True, padx=(30, 0), pady=(0, 20))
        scrollbar.pack(side='right', fill='y', pady=(0, 20), padx=(0, 30))
        self.canvas.bind_all('<MouseWheel>', lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        self.processes = []
        self.vars = {}

    def on_show(self):
        self.processes = self.engine.get_processes()
        self.render_list()

    def render_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        query = self.search_var.get().lower()
        if query == "search processes...": query = ""
        
        for i, proc in enumerate(self.processes):
            if query and query not in proc['name'].lower(): continue
            
            bg = BG_ROW1 if i % 2 == 0 else BG_ROW2
            row = tk.Frame(self.scroll_frame, bg=bg, pady=5)
            row.pack(fill='x')
            
            keep = proc['name'] in self.engine.whitelist
            var = tk.BooleanVar(value=keep)
            self.vars[proc['name']] = var
            
            tk.Checkbutton(row, variable=var, bg=bg, activebackground=bg, selectcolor=BG_HEADER, 
                           command=lambda n=proc['name'], v=var: self.toggle_keep(n, v)).pack(side='left', padx=10)
            
            name_color = GREEN if keep else TEXT_MAIN
            tk.Label(row, text=f"{proc['name']} (x{proc['instances']})" if proc['instances']>1 else proc['name'], 
                     bg=bg, fg=name_color, font=('Segoe UI', 10, 'bold' if keep else 'normal'), width=35, anchor='w').pack(side='left')
            
            tk.Label(row, text=f"{proc['cpu']:.1f}%", bg=bg, fg=TEXT_MAIN, font=('Segoe UI', 10), width=8).pack(side='right', padx=10)
            ram_color = RED if proc['ram'] > 400 else YELLOW if proc['ram'] > 100 else TEXT_MAIN
            tk.Label(row, text=f"{proc['ram']:.0f} MB", bg=bg, fg=ram_color, font=('Segoe UI', 10, 'bold'), width=10).pack(side='right')

    def toggle_keep(self, name, var):
        if var.get(): self.engine.whitelist.add(name)
        else: self.engine.whitelist.discard(name)
        self.engine.save_config()
        self.on_show()

    def do_kill_unmarked(self):
        def _kill():
            killed = 0
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and name.lower() not in SYSTEM_PROTECTED and name not in self.engine.whitelist:
                        proc.kill()
                        killed += 1
                except: pass
            time.sleep(0.5)
            self.app.root.after(0, self.on_show)
        threading.Thread(target=_kill, daemon=True).start()

    def toggle_auto(self):
        self.app.auto_kill_active = not self.app.auto_kill_active
        if self.app.auto_kill_active:
            self.auto_btn.config(text="⏹ Auto-Kill ON", bg=BTN_STOP)
            threading.Thread(target=self.auto_kill_loop, daemon=True).start()
        else:
            self.auto_btn.config(text="▶ Auto-Kill OFF", bg=BTN_AUTO)

    def auto_kill_loop(self):
        while self.app.auto_kill_active:
            time.sleep(self.engine.config.get('auto_kill_interval', 10))
            if not self.app.auto_kill_active: break
            
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and name.lower() not in SYSTEM_PROTECTED and name not in self.engine.whitelist:
                        proc.kill()
                except: pass

class CleanupView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        tk.Label(self, text="System Cleanup", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', padx=30, pady=20)
        
        info = tk.Label(self, text="Safely clean Windows Temp files and Prefetch to free up space.\n(Requires Admin privileges for some files)", 
                        bg=BG_MAIN, fg=TEXT_DIM, font=('Segoe UI', 11), justify='left')
        info.pack(anchor='w', padx=30, pady=(0, 20))

        self.status_var = tk.StringVar(value="Ready to scan.")
        tk.Label(self, textvariable=self.status_var, bg=BG_CARD, fg=ACCENT, font=('Segoe UI', 12, 'bold'), padx=20, pady=20).pack(fill='x', padx=30, pady=10)

        tk.Button(self, text="🧹 Clean System Junk", bg=MAGENTA, fg='white', font=('Segoe UI', 12, 'bold'), 
                  relief='flat', padx=20, pady=10, command=self.do_clean).pack(pady=20)

    def do_clean(self):
        self.status_var.set("Scanning and cleaning... Please wait.")
        self.update()
        
        def _clean():
            paths_to_clean = [
                os.path.expandvars("%TEMP%"),
                r"C:\Windows\Temp",
                r"C:\Windows\Prefetch"
            ]
            
            cleaned_mb = 0
            file_count = 0
            
            for path in paths_to_clean:
                if not os.path.exists(path): continue
                for root, dirs, files in os.walk(path):
                    for name in files:
                        filepath = os.path.join(root, name)
                        try:
                            size = os.path.getsize(filepath)
                            os.remove(filepath)
                            cleaned_mb += size
                            file_count += 1
                        except: pass
                    for name in dirs:
                        dirpath = os.path.join(root, name)
                        try: shutil.rmtree(dirpath)
                        except: pass
            
            cleaned_mb = cleaned_mb / (1024 * 1024)
            self.status_var.set(f"✅ Cleanup Complete! Deleted {file_count} files ({cleaned_mb:.2f} MB freed).")
        
        threading.Thread(target=_clean, daemon=True).start()

class MemoryView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        tk.Label(self, text="RAM Optimizer", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', padx=30, pady=20)
        
        tk.Label(self, text="Flush standby RAM and working sets to liberate captive memory.\nGreat to run right before starting a stream or game.", 
                 bg=BG_MAIN, fg=TEXT_DIM, font=('Segoe UI', 11), justify='left').pack(anchor='w', padx=30, pady=(0, 20))

        self.ram_inf = tk.StringVar()
        self.update_ram_info()
        tk.Label(self, textvariable=self.ram_inf, bg=BG_CARD, fg=TEXT_MAIN, font=('Segoe UI', 14), padx=20, pady=20, justify='left').pack(fill='x', padx=30, pady=10)

        tk.Button(self, text="💾 Optimize RAM Now", bg=ACCENT, fg=BG_MAIN, font=('Segoe UI', 12, 'bold'), 
                  relief='flat', padx=20, pady=10, command=self.do_optimize).pack(pady=20)

    def on_show(self):
        self.update_ram_info()

    def update_ram_info(self):
        mem = psutil.virtual_memory()
        total = mem.total / (1024**3)
        available = mem.available / (1024**3)
        used = mem.used / (1024**3)
        self.ram_inf.set(f"Total RAM: {total:.1f} GB\nUsed: {used:.1f} GB\nAvailable: {available:.1f} GB")

    def do_optimize(self):
        self.engine.optimize_ram()
        time.sleep(0.5)
        self.update_ram_info()
        messagebox.showinfo("StreamBoost Memory", "RAM optimization command sent successfully!\nCheck the updated Available RAM.")

class ProfilesView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        self.app = app
        tk.Label(self, text="Stream / Game Profiles", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', padx=30, pady=20)
        tk.Label(self, text="Select a profile to quickly change which apps are kept alive.", 
                 bg=BG_MAIN, fg=TEXT_DIM, font=('Segoe UI', 11), justify='left').pack(anchor='w', padx=30, pady=(0, 20))

        self.profile_frame = tk.Frame(self, bg=BG_MAIN)
        self.profile_frame.pack(fill='x', padx=30)
        self.render_profiles()

    def render_profiles(self):
        for w in self.profile_frame.winfo_children(): w.destroy()
        
        for pname, plist in self.engine.config['profiles'].items():
            f = tk.Frame(self.profile_frame, bg=BG_CARD, padx=15, pady=15)
            f.pack(fill='x', pady=5)
            
            tk.Label(f, text=pname, bg=BG_CARD, fg=ACCENT if self.engine.config.get('active_profile') == pname else TEXT_MAIN, 
                     font=('Segoe UI', 12, 'bold')).pack(side='left')
            
            tk.Button(f, text="Load Profile", bg=BG_HEADER, fg=TEXT_MAIN, relief='flat', padx=10, 
                      command=lambda p=pname, l=plist: self.load_profile(p, l)).pack(side='right')

    def load_profile(self, name, whitelist_list):
        self.engine.whitelist = set(whitelist_list)
        self.engine.config['active_profile'] = name
        self.engine.save_config()
        self.render_profiles()
        messagebox.showinfo("Profile Loaded", f"Profile '{name}' loaded.\nProcess whitelist updated.")

class SettingsView(tk.Frame):
    def __init__(self, parent, engine, app):
        super().__init__(parent, bg=BG_MAIN)
        self.engine = engine
        tk.Label(self, text="Settings", font=('Segoe UI', 20, 'bold'), bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor='w', padx=30, pady=20)

        f = tk.Frame(self, bg=BG_CARD, padx=20, pady=20)
        f.pack(fill='x', padx=30)

        # Interval
        tk.Label(f, text="Auto-Kill Interval (seconds):", bg=BG_CARD, fg=TEXT_MAIN, font=('Segoe UI', 11)).grid(row=0, column=0, sticky='w', pady=10)
        self.int_var = tk.StringVar(value=str(self.engine.config.get('auto_kill_interval', 10)))
        tk.Entry(f, textvariable=self.int_var, bg=BG_MAIN, fg=ACCENT, font=('Segoe UI', 11)).grid(row=0, column=1, padx=20, pady=10)

        # Minimize to Tray
        self.tray_var = tk.BooleanVar(value=self.engine.config.get('minimize_to_tray', True))
        tk.Checkbutton(f, text="Minimize to System Tray on close", variable=self.tray_var, bg=BG_CARD, fg=TEXT_MAIN, 
                       selectcolor=BG_HEADER, activebackground=BG_CARD, font=('Segoe UI', 11)).grid(row=1, column=0, columnspan=2, sticky='w', pady=10)

        tk.Button(self, text="Save Settings", bg=BTN_AUTO, fg='white', font=('Segoe UI', 12, 'bold'), 
                  relief='flat', padx=20, pady=10, command=self.save_settings).pack(pady=20, anchor='w', padx=30)

    def save_settings(self):
        try:
            self.engine.config['auto_kill_interval'] = int(self.int_var.get())
        except: pass
        self.engine.config['minimize_to_tray'] = self.tray_var.get()
        self.engine.save_config()
        messagebox.showinfo("Settings", "Settings saved successfully!")

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # DPI aware
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

    root = tk.Tk()
    # Set icon if exists
    if os.path.exists("streamboost_icon.ico"):
        try: root.iconbitmap("streamboost_icon.ico")
        except: pass

    # Optional: Admin check warning
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    
    engine = StreamBoostEngine()
    app = StreamBoostUI(root, engine)
    
    if not is_admin:
        messagebox.showwarning("Admin Rights Recommended", "StreamBoost is not running as Administrator.\nRAM Optimization and Temp Cleanup might not work fully.")
        
    root.mainloop()
