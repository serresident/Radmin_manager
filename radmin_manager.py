import sys
import csv
import struct
import math
import tempfile
import subprocess
import os
import json
import threading
import time
import re
import ctypes
import ctypes.wintypes as wt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog, 
                             QMessageBox, QAbstractItemView, QMenu, QTextEdit, QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt

user32 = ctypes.WinDLL("user32", use_last_error=True)
WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
VK_RETURN = 0x0D

EnumChildProc = ctypes.WINFUNCTYPE(
    wt.BOOL,
    wt.HWND,
    wt.LPARAM
)

user32.EnumChildWindows.argtypes = [wt.HWND, EnumChildProc, wt.LPARAM]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wt.HWND
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, ctypes.c_void_p]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

RADMIN_RE = re.compile(r"(Radmin).*[:：]\s*(.+)", re.IGNORECASE)
WINDOWS_RE = re.compile(r"(Windows).*[:：]\s*(.+)", re.IGNORECASE)

class RadminAutoFill:
    def __init__(self):
        self.radmin_re = RADMIN_RE
        self.windows_re = WINDOWS_RE

    def is_login_window(self, title):
        return bool(self.radmin_re.search(title) or self.windows_re.search(title))

    def get_window_text(self, hwnd):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, len(buf))
        return buf.value

    def get_login_type(self, title):
        if self.radmin_re.search(title):
            return "radmin"
        if self.windows_re.search(title):
            return "windows"
        return None

    def find_login_controls(self, hwnd):
        title = self.get_window_text(hwnd)
        login_type = self.get_login_type(title)
        if login_type is None:
            return None

        controls = {
            "username": None,
            "password": None,
            "domain": None,
            "ok": None,
            "cancel": None,
            "checkbox": None,
        }
        state = {"tab": 0}

        @EnumChildProc
        def callback(child, lParam):
            idx = state["tab"]

            if login_type == "radmin":
                if idx == 0:
                    controls["username"] = child
                elif idx == 2:
                    controls["password"] = child
                elif idx == 4:
                    controls["checkbox"] = child
                elif idx == 5:
                    controls["ok"] = child
                elif idx == 6:
                    controls["cancel"] = child
            else:  # windows
                if idx == 0:
                    controls["username"] = child
                elif idx == 2:
                    controls["password"] = child
                elif idx == 4:
                    controls["domain"] = child
                elif idx == 6:
                    controls["checkbox"] = child
                elif idx == 7:
                    controls["ok"] = child
                elif idx == 8:
                    controls["cancel"] = child

            state["tab"] += 1
            return True

        user32.EnumChildWindows(hwnd, callback, 0)
        controls["login_type"] = login_type
        controls["title"] = title
        return controls

    def fill_credentials(self, controls, username, password, domain=None, auto_enter=False):
        if controls["username"]:
            buf = ctypes.create_unicode_buffer(username)
            user32.SendMessageW(controls["username"], WM_SETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p))
        if controls["password"]:
            buf = ctypes.create_unicode_buffer(password)
            user32.SendMessageW(controls["password"], WM_SETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p))
        if domain and controls["domain"]:
            buf = ctypes.create_unicode_buffer(domain)
            user32.SendMessageW(controls["domain"], WM_SETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p))
        if auto_enter and controls["ok"]:
            user32.PostMessageW(controls["ok"], WM_KEYDOWN, VK_RETURN, 0)

    def try_autofill_foreground(self, username, password, domain=None, auto_enter=False):
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        title = self.get_window_text(hwnd)
        if not self.is_login_window(title):
            return False

        controls = self.find_login_controls(hwnd)
        if not controls:
            return False

        self.fill_credentials(controls, username, password, domain, auto_enter)
        return True

class RadminUltimateEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radmin Book Manager (RPB Editor)")
        self.resize(900, 600)
        
        # Путь к Radmin (поменяйте, если он установлен в другое место)
        self.radmin_path = r"C:\Program Files (x86)\Radmin Viewer 3\Radmin.exe"
        self.credentials_path = os.path.join(os.path.dirname(__file__), "radmin_credentials.json")
        self.credentials = self.load_credentials_json()
        self.autofill = RadminAutoFill()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # --- ПАНЕЛЬ ФАЙЛОВ ---
        file_layout = QHBoxLayout()
        self.btn_open_rpb = QPushButton("📂 Открыть .rpb")
        self.btn_open_rpb.clicked.connect(self.load_rpb)
        
        self.btn_save_rpb = QPushButton("💾 Сохранить .rpb")
        self.btn_save_rpb.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save_rpb.clicked.connect(self.save_rpb_dialog)
        
        self.btn_import_csv = QPushButton("📥 Импорт CSV")
        self.btn_import_csv.clicked.connect(self.load_csv)
        
        self.btn_export_csv = QPushButton("📤 Экспорт CSV")
        self.btn_export_csv.clicked.connect(self.save_csv)
        
        file_layout.addWidget(self.btn_open_rpb)
        file_layout.addWidget(self.btn_save_rpb)
        file_layout.addWidget(self.btn_import_csv)
        file_layout.addWidget(self.btn_export_csv)
        layout.addLayout(file_layout)
        
        # --- ПАНЕЛЬ ПОИСКА ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Быстрый поиск по имени, IP или логину...")
        self.search_bar.setStyleSheet("font-size: 13px; padding: 4px;")
        self.search_bar.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search_bar)
        
        # --- ДЕРЕВО ЗАПИСЕЙ ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(8)
        self.tree.setHeaderLabels(["Имя записи", "IP / Адрес", "Порт", "Логин", "Пароль", "Домен", "ТипАвторизации", "Тип"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(3, 120)
        self.tree.setColumnWidth(4, 120)
        self.tree.setColumnWidth(5, 150)
        self.tree.setColumnWidth(6, 120)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # Контекстное меню
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.itemChanged.connect(self.on_item_changed)
        
        layout.addWidget(self.tree)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: Consolas, monospace; background-color: #1e1e1e; color: #d4d4d4;")
        self.log_area.setFixedHeight(120)
        layout.addWidget(self.log_area)
        
        # --- ПАНЕЛЬ РЕДАКТИРОВАНИЯ ---
        edit_layout = QHBoxLayout()
        self.btn_add_folder = QPushButton("📁 Добавить папку")
        self.btn_add_folder.clicked.connect(lambda: self.add_item(True))
        
        self.btn_add_host = QPushButton("💻 Добавить хост")
        self.btn_add_host.clicked.connect(lambda: self.add_item(False))
        
        self.btn_delete = QPushButton("❌ Удалить")
        self.btn_delete.clicked.connect(self.delete_item)
        
        edit_layout.addWidget(self.btn_add_folder)
        edit_layout.addWidget(self.btn_add_host)
        edit_layout.addWidget(self.btn_delete)
        layout.addLayout(edit_layout)

    # --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
    def read_utf16(self, data, offset, max_size):
        raw_bytes = data[offset:offset+max_size]
        try: return raw_bytes.decode('utf-16le').split('\x00')[0]
        except: return ""

    def write_utf16(self, buffer, offset, text):
        b_text = text.encode('utf-16le')[:198]
        buffer[offset:offset+len(b_text)] = b_text

    def read_utf16_any(self, data, offsets, max_size):
        for offset in offsets:
            value = self.read_utf16(data, offset, max_size)
            if value:
                return value
        return ""

    def cred_key(self, row_data):
        return f"{row_data.get('Адрес','').strip().lower()}|{row_data.get('Порт','4899')}"

    def load_credentials_json(self):
        try:
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить credentials: {e}")
        return {}

    def save_credentials_json(self):
        try:
            with open(self.credentials_path, "w", encoding="utf-8") as f:
                json.dump(self.credentials, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Не удалось сохранить credentials: {e}")

    def on_item_changed(self, item, column):
        row_data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        row_data.update({
            'ИмяЗаписи': item.text(0),
            'Адрес': item.text(1),
            'Порт': item.text(2) or "4899",
            'Логин': item.text(3),
            'Пароль': item.text(4),
            'Домен': item.text(5),
            'ТипАвторизации': item.text(6) or "Radmin",
            'ЭтоГруппа': "1" if item.text(7) == "📁 Папка" else "0"
        })
        item.setData(0, Qt.ItemDataRole.UserRole, row_data)
        if row_data['ЭтоГруппа'] == "0" and row_data['Адрес']:
            self.credentials[self.cred_key(row_data)] = row_data.get('Пароль', "")
            self.save_credentials_json()

    def create_tree_item(self, row_data):
        is_group = str(row_data.get("ЭтоГруппа", "0")) == "1"
        item = QTreeWidgetItem([
            row_data.get("ИмяЗаписи", ""),
            row_data.get("Адрес", "") if not is_group else "",
            str(row_data.get("Порт", "4899")) if not is_group else "",
            row_data.get("Логин", "") if not is_group else "",
            row_data.get("Пароль", "") if not is_group else "",
            row_data.get("Домен", "") if not is_group else "",
            row_data.get("ТипАвторизации", "Radmin") if not is_group else "",
            "📁 Папка" if is_group else "💻 Хост"
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, row_data)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        return item

    def log(self, text):
        self.log_area.append(text)
        QApplication.processEvents()

    def build_tree_from_list(self, flat_list):
        self.tree.clear()
        items_map = {}
        for row in flat_list:
            if 'Пароль' not in row or not row.get('Пароль'):
                row['Пароль'] = self.credentials.get(self.cred_key(row), "")
            if 'Домен' not in row:
                row['Домен'] = ""
            if 'ТипАвторизации' not in row:
                row['ТипАвторизации'] = "Radmin"
            rec_id = str(row.get("ИДЗаписи", "0"))
            items_map[rec_id] = {"item": self.create_tree_item(row), "parent_id": str(row.get("ИДРодителя", "0"))}

        for node in items_map.values():
            p_id = node["parent_id"]
            if p_id in items_map and p_id != "0":
                items_map[p_id]["item"].addChild(node["item"])
            else:
                self.tree.addTopLevelItem(node["item"])
        self.tree.expandAll()

    # --- ЛОГИКА ИНТЕРФЕЙСА ---
    def add_item(self, is_group):
        name = "Новая папка" if is_group else "Новый хост"
        data = {"ИмяЗаписи": name, "ЭтоГруппа": "1" if is_group else "0", "Порт": 4899, "Пароль": "", "Домен": "", "ТипАвторизации": "Radmin"}
        item = self.create_tree_item(data)
        parent = self.tree.currentItem()
        if parent and parent.text(7) == "📁 Папка":
            parent.addChild(item)
            parent.setExpanded(True)
        else:
            self.tree.addTopLevelItem(item)

    def delete_item(self):
        for item in self.tree.selectedItems():
            (item.parent() or self.tree.invisibleRootItem()).removeChild(item)

    def filter_tree(self, text):
        text = text.lower()
        root = self.tree.invisibleRootItem()
        
        def filter_item(item):
            # Ищем по имени (0), IP (1) или логину (3)
            match = text in item.text(0).lower() or text in item.text(1).lower() or text in item.text(3).lower()
            child_match = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    child_match = True
            
            show = match or child_match
            item.setHidden(not show)
            if text and child_match:
                item.setExpanded(True)
            return show
            
        for i in range(root.childCount()):
            filter_item(root.child(i))

    def add_to_favorites(self, item):
        root = self.tree.invisibleRootItem()
        fav_folder = next((root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "⭐ Избранное" and root.child(i).text(7) == "📁 Папка"), None)
                
        if not fav_folder:
            fav_data = {"ИмяЗаписи": "⭐ Избранное", "ЭтоГруппа": "1", "Порт": 4899, "Пароль": "", "Домен": "", "ТипАвторизации": "Radmin"}
            fav_folder = self.create_tree_item(fav_data)
            self.tree.insertTopLevelItem(0, fav_folder) # Добавляем в самый верх списка
            
        fav_item = self.create_tree_item(item.data(0, Qt.ItemDataRole.UserRole).copy())
        fav_folder.addChild(fav_item)
        fav_folder.setExpanded(True)
        self.tree.scrollToItem(fav_item)

    def set_credentials_for_folder(self, folder_item):
        """Задает логин и пароль для всех дочерних хостов в папке."""
        new_login, ok1 = QInputDialog.getText(self, "Массовое изменение", "Введите новый логин для всех хостов в папке:")
        if not ok1:
            return

        new_password, ok2 = QInputDialog.getText(self, "Массовое изменение", f"Введите новый пароль для логина '{new_login}':", QLineEdit.EchoMode.Password)
        if not ok2:
            return

        # Блокируем сигналы, чтобы on_item_changed не вызывался для каждого элемента
        self.tree.blockSignals(True)
        
        items_updated = 0
        def update_children(parent_item):
            nonlocal items_updated
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                # Если дочерний элемент - хост, меняем данные
                if child.text(7) == "💻 Хост":
                    child.setText(3, new_login)
                    child.setText(4, new_password)
                    
                    # Обновляем и внутренние данные
                    row_data = child.data(0, Qt.ItemDataRole.UserRole) or {}
                    row_data['Логин'] = new_login
                    row_data['Пароль'] = new_password
                    child.setData(0, Qt.ItemDataRole.UserRole, row_data)
                    
                    # Обновляем словарь паролей
                    if row_data.get('Адрес'):
                         self.credentials[self.cred_key(row_data)] = new_password
                    items_updated += 1
                # Если дочерний элемент - папка, рекурсивно идем вглубь
                elif child.text(7) == "📁 Папка":
                    update_children(child)
        
        update_children(folder_item)
        
        # Разблокируем сигналы
        self.tree.blockSignals(False)
        
        if items_updated > 0:
            self.save_credentials_json() # Сохраняем все изменения в JSON один раз
            QMessageBox.information(self, "Готово", f"Обновлено {items_updated} хостов в папке '{folder_item.text(0)}'.")
        else:
            QMessageBox.information(self, "Внимание", f"В папке '{folder_item.text(0)}' не найдено хостов для обновления.")

    # --- ЗАПУСК RADMIN (АВТОМАТИЗАЦИЯ) ---
    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        
        # Контекстное меню для ПАПКИ
        if item.text(7) == "📁 Папка":
            action_set_creds = menu.addAction("🔑 Задать логин/пароль для всех хостов")
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            
            if action == action_set_creds:
                self.set_credentials_for_folder(item)
            return

        # Контекстное меню для ХОСТА
        if item.text(7) == "💻 Хост":
            a_full = menu.addAction("⚡ Управление")
            a_view = menu.addAction("👁 Просмотр (/noinput)")
            a_telnet = menu.addAction("📟 Telnet")
            a_file = menu.addAction("📁 Передача файлов")
            menu.addSeparator()
            a_fav = menu.addAction("⭐ Добавить в Избранное")
            
            action = menu.exec(self.tree.viewport().mapToGlobal(position))
            if not action: return
            
            if action == a_fav:
                self.add_to_favorites(item)
                return
            
            if not os.path.exists(self.radmin_path):
                QMessageBox.warning(self, "Ошибка", "Не найден Radmin.exe по пути: " + self.radmin_path)
                return

            temp_rpb = os.path.join(tempfile.gettempdir(), "radmin_launcher_temp.rpb")
            self.save_to_rpb_file(temp_rpb)
            rec_id = item.data(0, Qt.ItemDataRole.UserRole).get("ИДЗаписи")
            cmd_line = f'"{self.radmin_path}" /pbpath"{temp_rpb}" /pbid:{rec_id}'
            username = item.text(3)
            password = item.text(4)
            
            self.log(f"[DEBUG] temp_rpb = {temp_rpb}")
            self.log(f"[DEBUG] rec_id = {rec_id}")
            self.log(f"[DEBUG] cmd_line = {cmd_line}")
            
            try:
                if action == a_full:
                    self.log(f"[INFO] Попытка открыть Управление для {item.text(0)} ({item.text(1)}:{item.text(2)})")
                    self.launch_radmin_and_autofill(cmd_line, username, password, auto_enter=True)
                elif action == a_view:
                    self.log(f"[INFO] Попытка открыть Просмотр для {item.text(0)}")
                    self.launch_radmin_and_autofill(cmd_line + " /noinput", username, password, auto_enter=True)
                elif action == a_telnet:
                    self.log(f"[INFO] Попытка открыть Telnet для {item.text(0)} ({item.text(1)}:{item.text(2)})")
                    self.launch_radmin_and_autofill(cmd_line + " /telnet", username, password, auto_enter=True)
                elif action == a_file:
                    self.log(f"[INFO] Попытка передать файл для {item.text(0)}")
                    self.launch_radmin_and_autofill(cmd_line + " /file", username, password, auto_enter=True)
            except Exception as e:
                self.log(f"[ERROR] Ошибка запуска: {e}")
                QMessageBox.critical(self, "Ошибка запуска", str(e))

    def launch_radmin_and_autofill(self, cmd_line, username, password, auto_enter=False):
        subprocess.Popen(cmd_line, shell=True)
        if not username or not password:
            return

        def worker():
            for _ in range(20):
                time.sleep(0.5)
                if self.autofill.try_autofill_foreground(username, password, auto_enter=auto_enter):
                    self.log("[INFO] Автозаполнил логин/пароль")
                    return
            self.log("[WARN] Не удалось автозаполнить форму Radmin")

        threading.Thread(target=worker, daemon=True).start()

    # --- ЧТЕНИЕ И ЗАПИСЬ .RPB ---
    def load_rpb(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть .rpb", "", "Radmin Book (*.rpb)")
        if not path: return
        
        try:
            with open(path, "rb") as f:
                data = f.read()
            
            if len(data) < 25: return
            offset = 25
            hosts = []
            
            while offset < len(data):
                page_index = data[offset:offset+128]
                offset += 128
                for i in range(128):
                    if offset + 6138 > len(data): break
                    seg = data[offset:offset+6138]
                    offset += 6138
                    
                    if page_index[i] == 1:
                        hosts.append({
                            "ИДЗаписи": struct.unpack_from("<I", seg, 6112)[0],
                            "ИДРодителя": struct.unpack_from("<I", seg, 6120)[0],
                            "ЭтоГруппа": "1" if seg[6124] == 1 else "0",
                            "ИмяЗаписи": self.read_utf16(seg, 5104, 200),
                            "Адрес": self.read_utf16(seg, 4904, 200),
                            "Логин": self.read_utf16(seg, 5308, 200) or self.read_utf16_any(seg, [5320, 5340, 5360, 5380, 5400], 200),
                            "Домен": self.read_utf16(seg, 5508, 200),
                            "ТипАвторизации": "Radmin" if struct.unpack_from("<I", seg, 6108)[0] == 0 else "Windows",
                            "Порт": struct.unpack_from("<I", seg, 5304)[0]
                        })
            self.build_tree_from_list(hosts)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать RPB:\n{e}")

    def save_rpb_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить .rpb", "addressbook.rpb", "Radmin Book (*.rpb)")
        if path:
            self.save_to_rpb_file(path)
            QMessageBox.information(self, "Успех", "Файл успешно сохранен!")

    def save_to_rpb_file(self, filepath):
        """Рекурсивно обходит дерево, пересчитывает ID и собирает бинарник"""
        flat_list = []
        self.current_id = 1 
        
        def traverse(parent_item, parent_id):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                my_id = self.current_id
                self.current_id += 1
                
                row_data = child.data(0, Qt.ItemDataRole.UserRole) or {}
                row_data.update({
                    'ИмяЗаписи': child.text(0), 'Адрес': child.text(1), 
                    'Порт': child.text(2) or "4899", 'Логин': child.text(3), 'Пароль': child.text(4),
                    'Домен': child.text(5), 'ТипАвторизации': child.text(6) or "Radmin",
                    'ЭтоГруппа': "1" if child.text(7) == "📁 Папка" else "0",
                    'ИДЗаписи': my_id, 'ИДРодителя': parent_id
                })
                # Обновляем данные в элементе UI (нужно для авто-запуска)
                child.setData(0, Qt.ItemDataRole.UserRole, row_data)
                
                flat_list.append(row_data)
                traverse(child, my_id)
                
        traverse(self.tree.invisibleRootItem(), 0)
        
        try:
            unknown_a = b'\x01\x00\x00\x00' + b'\x00' * 116
            unknown_b = b'\x02\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00' + b'\x00' * 2564
            header = bytes.fromhex("040000000000000000000000fa170000800000000100000001")
            
            total = len(flat_list)
            pages = math.ceil(total / 128) if total else 1
            
            with open(filepath, "wb") as f:
                f.write(header)
                idx = 0
                for _ in range(pages):
                    in_page = min(128, total - idx)
                    f.write(bytearray([1] * in_page + [0] * (128 - in_page)))
                    for i in range(128):
                        seg = bytearray(6138)
                        if i < in_page:
                            row = flat_list[idx]
                            idx += 1
                            struct.pack_into("<I", seg, 0, 100)
                            struct.pack_into("<I", seg, 24, 1)
                            seg[28:148] = unknown_a             
                            struct.pack_into("<I", seg, 148, 5)
                            seg[2328:4904] = unknown_b          
                            
                            struct.pack_into("<I", seg, 6112, int(row["ИДЗаписи"]))
                            struct.pack_into("<I", seg, 6120, int(row["ИДРодителя"]))
                            seg[6124] = 1 if row["ЭтоГруппа"] == "1" else 0
                            
                            self.write_utf16(seg, 5104, row["ИмяЗаписи"])
                            self.write_utf16(seg, 4904, row["Адрес"])
                            self.write_utf16(seg, 5308, row["Логин"])
                            self.write_utf16(seg, 5508, row.get("Домен", ""))
                            struct.pack_into("<I", seg, 5304, int(row["Порт"]))
                            struct.pack_into("<I", seg, 6108, 1 if row.get("ТипАвторизации", "Radmin") == "Radmin" else 0)
                        f.write(seg)
        except Exception as e:
            print("Ошибка записи:", e)

    # --- ЧТЕНИЕ И ЗАПИСЬ CSV ---
    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт CSV", "", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                self.build_tree_from_list(list(csv.DictReader(f, delimiter=";")))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт CSV", "hosts.csv", "CSV Files (*.csv)")
        if not path: return
        
        flat_list = []
        def traverse(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                flat_list.append(child.data(0, Qt.ItemDataRole.UserRole))
                traverse(child)
        traverse(self.tree.invisibleRootItem())
        
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["ИДЗаписи", "ИДРодителя", "ЭтоГруппа", "ИмяЗаписи", "Адрес", "Порт", "Логин", "Пароль", "Домен", "ТипАвторизации"], delimiter=";")
                writer.writeheader()
                writer.writerows(flat_list)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadminUltimateEditor()
    window.show()
    sys.exit(app.exec())
