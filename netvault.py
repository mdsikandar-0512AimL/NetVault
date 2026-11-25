import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import datetime
import difflib
import os

DB_NAME = "network_config_store.db"


class DatabaseManager:
    """Handles all SQLite database operations for routers and config versions."""

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Table 1: Router Inventory
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE NOT NULL,
                ip_address TEXT NOT NULL,
                vendor TEXT NOT NULL,
                model TEXT,
                location TEXT,
                created_at TEXT
            )
        ''')

        # Table 2: Configuration Store (Versioned History)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                router_id INTEGER NOT NULL,
                version_num INTEGER NOT NULL,
                config_type TEXT NOT NULL,
                config_text TEXT NOT NULL,
                commit_note TEXT,
                saved_at TEXT NOT NULL,
                FOREIGN KEY (router_id) REFERENCES routers (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()

        # Pre-populate with sample data if empty (great for college demos)
        cursor.execute("SELECT COUNT(*) FROM routers")
        if cursor.fetchone()[0] == 0:
            self.seed_sample_data(conn)

        conn.close()

    def seed_sample_data(self, conn):
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        samples = [
            ("CORE-RTR-01", "10.0.0.1", "Cisco IOS", "ISR 4451", "Main Data Center",
             "!\nhostname CORE-RTR-01\n!\ninterface GigabitEthernet0/0/0\n description Uplink to ISP\n ip address 203.0.113.2 255.255.255.252\n no shutdown\n!\nrouter ospf 1\n network 10.0.0.0 0.0.255.255 area 0\n!\nline vty 0 4\n transport input ssh\n!\nend"),
            ("EDGE-FW-02", "192.168.10.1", "Juniper Junos", "SRX340", "Branch Office - North",
             "system {\n    host-name EDGE-FW-02;\n    services {\n        ssh;\n    }\n}\ninterfaces {\n    ge-0/0/0 {\n        unit 0 {\n            family inet {\n                address 192.168.10.1/24;\n            }\n        }\n    }\n}"),
            ("CAMPUS-GW-03", "172.16.1.1", "MikroTik", "CCR2004", "Engineering Block",
             "/system identity set name=CAMPUS-GW-03\n/ip address add address=172.16.1.1/24 interface=ether1\n/ip dns set servers=8.8.8.8,1.1.1.1\n/ip firewall filter add chain=input protocol=tcp dst-port=22 action=accept")
        ]

        for host, ip, vendor, model, loc, cfg in samples:
            cursor.execute(
                "INSERT INTO routers (hostname, ip_address, vendor, model, location, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (host, ip, vendor, model, loc, now)
            )
            r_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO config_versions (router_id, version_num, config_type, config_text, commit_note, saved_at) VALUES (?, ?, ?, ?, ?, ?)",
                (r_id, 1, "startup-config", cfg, "Initial baseline configuration", now)
            )
        conn.commit()

    def add_router(self, hostname, ip, vendor, model, location, initial_config=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute(
                "INSERT INTO routers (hostname, ip_address, vendor, model, location, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (hostname, ip, vendor, model, location, now)
            )
            router_id = cursor.lastrowid
            if not initial_config.strip():
                initial_config = f"!\nhostname {hostname}\n! Management IP: {ip}\n! Add interface and routing configurations here...\nend"

            cursor.execute(
                "INSERT INTO config_versions (router_id, version_num, config_type, config_text, commit_note, saved_at) VALUES (?, ?, ?, ?, ?, ?)",
                (router_id, 1, "startup-config", initial_config, "Initial router provisioning", now)
            )
            conn.commit()
            return True, "Router added successfully."
        except sqlite3.IntegrityError:
            return False, f"A router with hostname '{hostname}' already exists."
        finally:
            conn.close()

    def update_router_details(self, router_id, hostname, ip, vendor, model, location):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE routers SET hostname=?, ip_address=?, vendor=?, model=?, location=? WHERE id=?",
                (hostname, ip, vendor, model, location, router_id)
            )
            conn.commit()
            return True, "Router metadata updated."
        except sqlite3.IntegrityError:
            return False, "Hostname must be unique."
        finally:
            conn.close()

    def delete_router(self, router_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM config_versions WHERE router_id=?", (router_id,))
        cursor.execute("DELETE FROM routers WHERE id=?", (router_id,))
        conn.commit()
        conn.close()

    def get_all_routers(self, search_query=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        if search_query:
            q = f"%{search_query}%"
            cursor.execute(
                "SELECT id, hostname, ip_address, vendor, model, location FROM routers WHERE hostname LIKE ? OR ip_address LIKE ? OR vendor LIKE ? OR location LIKE ? ORDER BY hostname ASC",
                (q, q, q, q)
            )
        else:
            cursor.execute("SELECT id, hostname, ip_address, vendor, model, location FROM routers ORDER BY hostname ASC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def save_new_config_version(self, router_id, config_type, config_text, commit_note):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version_num) FROM config_versions WHERE router_id=?", (router_id,))
        max_ver = cursor.fetchone()[0]
        next_ver = (max_ver or 0) + 1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO config_versions (router_id, version_num, config_type, config_text, commit_note, saved_at) VALUES (?, ?, ?, ?, ?, ?)",
            (router_id, next_ver, config_type, config_text, commit_note, now)
        )
        conn.commit()
        conn.close()
        return next_ver

    def get_config_versions(self, router_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, version_num, config_type, config_text, commit_note, saved_at FROM config_versions WHERE router_id=? ORDER BY version_num DESC",
            (router_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows


class RouterConfigApp:
    """Main GUI Application for Network Router Configuration Store."""

    def __init__(self, root):
        self.root = root
        self.root.title("NetVault — Network Router Configuration Store")
        self.root.geometry("1200x740")
        self.root.minsize(1000, 650)

        self.db = DatabaseManager()
        self.selected_router_id = None
        self.current_versions = []

        self.setup_styles()
        self.build_ui()
        self.refresh_router_list()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Color Palette
        self.bg_dark = "#1e293b"      # Slate 800
        self.bg_light = "#f8fafc"     # Slate 50
        self.accent = "#2563eb"       # Blue 600
        self.accent_hover = "#1d4ed8"
        self.text_dark = "#0f172a"

        self.root.configure(bg=self.bg_light)

        style.configure("TFrame", background=self.bg_light)
        style.configure("Header.TFrame", background=self.bg_dark)
        style.configure("Header.TLabel", background=self.bg_dark, foreground="white", font=("Segoe UI", 14, "bold"))
        style.configure("SubHeader.TLabel", background=self.bg_dark, foreground="#94a3b8", font=("Segoe UI", 9))

        style.configure("Card.TLabelframe", background=self.bg_light, font=("Segoe UI", 10, "bold"))
        style.configure("Card.TLabelframe.Label", background=self.bg_light, foreground=self.text_dark, font=("Segoe UI", 10, "bold"))

        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), foreground="white", background=self.accent, padding=6)
        style.map("Primary.TButton", background=[("active", self.accent_hover)])

        style.configure("Action.TButton", font=("Segoe UI", 9), padding=5)
        style.configure("Danger.TButton", font=("Segoe UI", 9), foreground="#dc2626", padding=5)

        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def build_ui(self):
        # --- Top Navigation / Banner ---
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(15, 10))
        header.pack(fill=tk.X)

        ttk.Label(header, text="NetVault | Network Router Configuration Store", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Centralized NVRAM / Startup-Config & Version Repository", style="SubHeader.TLabel").pack(side=tk.LEFT, padx=15)

        ttk.Button(header, text="+ Add New Router", style="Primary.TButton", command=self.open_add_router_dialog).pack(side=tk.RIGHT)

        # --- Main Split Layout (PanedWindow) ---
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ================= LEFT PANEL: Router Inventory =================
        left_frame = ttk.Labelframe(main_pane, text="Managed Routers Inventory", style="Card.TLabelframe", padding=8)
        main_pane.add(left_frame, weight=1)

        # Search Bar
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_router_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Router Treeview
        cols = ("hostname", "ip", "vendor")
        self.router_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.router_tree.heading("hostname", text="Hostname")
        self.router_tree.heading("ip", text="Management IP")
        self.router_tree.heading("vendor", text="OS / Vendor")

        self.router_tree.column("hostname", width=130)
        self.router_tree.column("ip", width=110)
        self.router_tree.column("vendor", width=100)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.router_tree.yview)
        self.router_tree.configure(yscrollcommand=scrollbar.set)

        self.router_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.router_tree.bind("<<TreeviewSelect>>", self.on_router_select)

        # Left Panel Bottom Buttons
        left_btn_frame = ttk.Frame(left_frame)
        left_btn_frame.pack(fill=tk.X, pady=(8, 0), side=tk.BOTTOM)

        # Re-pack tree above bottom buttons properly
        self.router_tree.pack_forget()
        scrollbar.pack_forget()
        left_btn_frame.pack(fill=tk.X, pady=(8, 0), side=tk.BOTTOM)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.router_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Button(left_btn_frame, text="Edit Device Info", style="Action.TButton", command=self.open_edit_router_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(left_btn_frame, text="Delete Router", style="Danger.TButton", command=self.delete_selected_router).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # ================= RIGHT PANEL: Configuration Workspace =================
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        # 1. Device Metadata Summary Bar
        meta_frame = ttk.Labelframe(right_frame, text="Device Details & Version Selector", style="Card.TLabelframe", padding=10)
        meta_frame.pack(fill=tk.X, pady=(0, 8))

        self.meta_label = ttk.Label(meta_frame, text="Select a router from the left inventory to view or manage its configuration store.", font=("Segoe UI", 10))
        self.meta_label.pack(anchor=tk.W)

        # Version Control Bar
        ver_bar = ttk.Frame(meta_frame)
        ver_bar.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(ver_bar, text="Stored Revision:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.version_combo = ttk.Combobox(ver_bar, state="readonly", width=48)
        self.version_combo.pack(side=tk.LEFT, padx=8)
        self.version_combo.bind("<<ComboboxSelected>>", self.on_version_select)

        ttk.Button(ver_bar, text="Compare with Previous (Diff)", style="Action.TButton", command=self.show_diff_window).pack(side=tk.LEFT, padx=4)
        ttk.Button(ver_bar, text="Import .cfg/.txt", style="Action.TButton", command=self.import_config_file).pack(side=tk.RIGHT, padx=2)
        ttk.Button(ver_bar, text="Export Backup", style="Action.TButton", command=self.export_config_file).pack(side=tk.RIGHT, padx=2)

        # 2. Configuration Editor Area
        editor_frame = ttk.Labelframe(right_frame, text="Configuration Store Editor (Startup-Config / Running-Config)", style="Card.TLabelframe", padding=8)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        text_scroll = ttk.Scrollbar(editor_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.config_editor = tk.Text(
            editor_frame,
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            undo=True,
            wrap=tk.NONE,
            yscrollcommand=text_scroll.set,
            padx=10,
            pady=10
        )
        self.config_editor.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.config_editor.yview)

        # 3. Commit / Save New Revision Footer
        commit_frame = ttk.Labelframe(right_frame, text="Commit Changes to NVRAM / Configuration Store", style="Card.TLabelframe", padding=8)
        commit_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(commit_frame, text="Config Type:").pack(side=tk.LEFT)
        self.config_type_var = tk.StringVar(value="startup-config")
        type_combo = ttk.Combobox(commit_frame, textvariable=self.config_type_var, values=["startup-config", "running-config", "golden-template"], state="readonly", width=16)
        type_combo.pack(side=tk.LEFT, padx=(5, 12))

        ttk.Label(commit_frame, text="Change Note:").pack(side=tk.LEFT)
        self.commit_note_var = tk.StringVar()
        note_entry = ttk.Entry(commit_frame, textvariable=self.commit_note_var)
        note_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))

        ttk.Button(commit_frame, text="Save New Config Version", style="Primary.TButton", command=self.commit_configuration).pack(side=tk.RIGHT)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready | Connected to SQLite Store: network_config_store.db")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(8, 3), font=("Segoe UI", 8))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ================= EVENT HANDLERS & LOGIC =================

    def refresh_router_list(self):
        query = self.search_var.get().strip()
        routers = self.db.get_all_routers(query)

        for item in self.router_tree.get_children():
            self.router_tree.delete(item)

        for r in routers:
            # r = (id, hostname, ip_address, vendor, model, location)
            self.router_tree.insert("", tk.END, iid=str(r[0]), values=(r[1], r[2], r[3]))

        self.status_var.set(f"Loaded {len(routers)} router(s) from configuration store.")

    def on_router_select(self, event):
        selected = self.router_tree.selection()
        if not selected:
            return

        self.selected_router_id = int(selected[0])
        routers = self.db.get_all_routers()
        router_info = next((r for r in routers if r[0] == self.selected_router_id), None)

        if router_info:
            _, host, ip, vendor, model, loc = router_info
            self.meta_label.config(
                text=f"Hostname: {host}   |   IP: {ip}   |   Platform: {vendor} ({model or 'N/A'})   |   Location: {loc or 'N/A'}"
            )

        self.load_router_versions()

    def load_router_versions(self):
        if not self.selected_router_id:
            return

        self.current_versions = self.db.get_config_versions(self.selected_router_id)
        combo_items = []
        for v in self.current_versions:
            # v = (id, version_num, config_type, config_text, commit_note, saved_at)
            combo_items.append(f"v{v[1]} [{v[2]}] - {v[5]} ({v[4]})")

        self.version_combo["values"] = combo_items
        if combo_items:
            self.version_combo.current(0)
            self.display_config_text(self.current_versions[0][3])
            self.config_type_var.set(self.current_versions[0][2])

    def on_version_select(self, event):
        idx = self.version_combo.current()
        if idx >= 0 and idx < len(self.current_versions):
            selected_ver = self.current_versions[idx]
            self.display_config_text(selected_ver[3])
            self.config_type_var.set(selected_ver[2])
            self.status_var.set(f"Viewing revision v{selected_ver[1]} saved on {selected_ver[5]}")

    def display_config_text(self, text):
        self.config_editor.delete("1.0", tk.END)
        self.config_editor.insert("1.0", text)

    def commit_configuration(self):
        if not self.selected_router_id:
            messagebox.showwarning("No Router Selected", "Please select a router from the left inventory first.")
            return

        config_text = self.config_editor.get("1.0", tk.END).strip()
        if not config_text:
            messagebox.showwarning("Empty Configuration", "Configuration content cannot be empty.")
            return

        note = self.commit_note_var.get().strip() or "Routine configuration update"
        cfg_type = self.config_type_var.get()

        new_ver = self.db.save_new_config_version(self.selected_router_id, cfg_type, config_text, note)
        self.commit_note_var.set("")
        self.load_router_versions()
        self.status_var.set(f"Saved configuration revision v{new_ver} successfully!")
        messagebox.showinfo("Configuration Saved", f"Configuration committed to store as Version v{new_ver}.")

    def import_config_file(self):
        if not self.selected_router_id:
            messagebox.showwarning("No Router Selected", "Select a router before importing a configuration file.")
            return

        file_path = filedialog.askopenfilename(
            title="Select Router Configuration File",
            filetypes=[("Config Files", "*.cfg *.txt *.conf"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.display_config_text(content)
                self.commit_note_var.set(f"Imported from {os.path.basename(file_path)}")
                self.status_var.set(f"Loaded {os.path.basename(file_path)} into editor. Click 'Save New Config Version' to commit.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to read file: {e}")

    def export_config_file(self):
        if not self.selected_router_id:
            messagebox.showwarning("No Router Selected", "Select a router to export its configuration.")
            return

        routers = self.db.get_all_routers()
        router_info = next((r for r in routers if r[0] == self.selected_router_id), None)
        hostname = router_info[1] if router_info else "router"
        idx = self.version_combo.current()
        ver_tag = f"v{self.current_versions[idx][1]}" if idx >= 0 else "backup"

        file_path = filedialog.asksaveasfilename(
            title="Export Router Configuration",
            initialfile=f"{hostname}_{ver_tag}.cfg",
            defaultextension=".cfg",
            filetypes=[("Router Config", "*.cfg"), ("Text File", "*.txt")]
        )
        if file_path:
            try:
                content = self.config_editor.get("1.0", tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.status_var.set(f"Exported configuration to {file_path}")
                messagebox.showinfo("Export Complete", f"Backup saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save file: {e}")

    def show_diff_window(self):
        if not self.selected_router_id or len(self.current_versions) < 2:
            messagebox.showinfo("Diff Unavailable", "At least 2 saved configuration versions are needed to compare changes.")
            return

        idx = self.version_combo.current()
        if idx == len(self.current_versions) - 1:
            messagebox.showinfo("Baseline Version", "This is the oldest (v1) baseline configuration. Select a newer version to compare against its predecessor.")
            return

        newer = self.current_versions[idx]
        older = self.current_versions[idx + 1]

        diff_lines = list(difflib.unified_diff(
            older[3].splitlines(),
            newer[3].splitlines(),
            fromfile=f"v{older[1]} ({older[5]})",
            tofile=f"v{newer[1]} ({newer[5]})",
            lineterm=""
        ))

        diff_win = tk.Toplevel(self.root)
        diff_win.title(f"Configuration Diff: v{older[1]} vs v{newer[1]}")
        diff_win.geometry("780x520")

        text_box = tk.Text(diff_win, font=("Consolas", 10), bg="#0f172a", fg="#e2e8f0", padx=10, pady=10)
        text_box.pack(fill=tk.BOTH, expand=True)

        text_box.tag_configure("added", foreground="#4ade80")    # Green
        text_box.tag_configure("removed", foreground="#f87171")  # Red
        text_box.tag_configure("header", foreground="#60a5fa")   # Blue

        if not diff_lines:
            text_box.insert(tk.END, "No differences detected between these two versions.")
        else:
            for line in diff_lines:
                if line.startswith("+") and not line.startswith("+++"):
                    text_box.insert(tk.END, line + "\n", "added")
                elif line.startswith("-") and not line.startswith("---"):
                    text_box.insert(tk.END, line + "\n", "removed")
                elif line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
                    text_box.insert(tk.END, line + "\n", "header")
                else:
                    text_box.insert(tk.END, line + "\n")

        text_box.config(state=tk.DISABLED)

    def delete_selected_router(self):
        if not self.selected_router_id:
            messagebox.showwarning("No Selection", "Please select a router to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this router and all its stored configuration history?")
        if confirm:
            self.db.delete_router(self.selected_router_id)
            self.selected_router_id = None
            self.current_versions = []
            self.meta_label.config(text="Select a router from the left inventory to view or manage its configuration store.")
            self.version_combo.set("")
            self.config_editor.delete("1.0", tk.END)
            self.refresh_router_list()

    # ================= MODAL DIALOGS (ADD / EDIT ROUTER) =================

    def open_add_router_dialog(self):
        self._open_router_form_dialog(mode="add")

    def open_edit_router_dialog(self):
        if not self.selected_router_id:
            messagebox.showwarning("No Selection", "Please select a router to edit.")
            return
        routers = self.db.get_all_routers()
        router_info = next((r for r in routers if r[0] == self.selected_router_id), None)
        self._open_router_form_dialog(mode="edit", router_data=router_info)

    def _open_router_form_dialog(self, mode="add", router_data=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Network Router" if mode == "add" else "Edit Router Details")
        dialog.geometry("460x440" if mode == "add" else "440x290")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Hostname *:", "hostname"),
            ("Management IP *:", "ip"),
            ("Vendor / OS *:", "vendor"),
            ("Hardware Model:", "model"),
            ("Physical Location:", "location")
        ]

        entries = {}
        for idx, (label_text, key) in enumerate(fields):
            ttk.Label(frame, text=label_text, font=("Segoe UI", 9, "bold")).grid(row=idx, column=0, sticky=tk.W, pady=6)
            if key == "vendor":
                var = tk.StringVar(value=router_data[3] if router_data else "Cisco IOS")
                widget = ttk.Combobox(frame, textvariable=var, values=["Cisco IOS", "Cisco NX-OS", "Juniper Junos", "MikroTik RouterOS", "Huawei VRP", "Arista EOS", "PfSense / OPNsense"], width=32)
            else:
                default_val = ""
                if router_data:
                    mapping = {"hostname": router_data[1], "ip": router_data[2], "model": router_data[4], "location": router_data[5]}
                    default_val = mapping.get(key, "")
                var = tk.StringVar(value=default_val)
                widget = ttk.Entry(frame, textvariable=var, width=35)
            widget.grid(row=idx, column=1, sticky=tk.EW, pady=6, padx=(10, 0))
            entries[key] = var

        config_box = None
        if mode == "add":
            ttk.Label(frame, text="Initial Config (Optional):", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky=tk.NW, pady=6)
            config_box = tk.Text(frame, height=6, width=35, font=("Consolas", 9))
            config_box.grid(row=5, column=1, sticky=tk.EW, pady=6, padx=(10, 0))

        def submit():
            h = entries["hostname"].get().strip()
            ip = entries["ip"].get().strip()
            v = entries["vendor"].get().strip()
            m = entries["model"].get().strip()
            loc = entries["location"].get().strip()

            if not h or not ip or not v:
                messagebox.showerror("Validation Error", "Hostname, Management IP, and Vendor are required.", parent=dialog)
                return

            if mode == "add":
                init_cfg = config_box.get("1.0", tk.END).strip()
                ok, msg = self.db.add_router(h, ip, v, m, loc, init_cfg)
            else:
                ok, msg = self.db.update_router_details(router_data[0], h, ip, v, m, loc)

            if ok:
                self.refresh_router_list()
                if mode == "edit":
                    self.on_router_select(None)
                dialog.destroy()
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Save Router", style="Primary.TButton", command=submit).pack(side=tk.RIGHT)


if __name__ == "__main__":
    root = tk.Tk()
    app = RouterConfigApp(root)
    root.mainloop()