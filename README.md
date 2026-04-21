Вот качественный перевод описания твоего приложения на английский язык. Я сохранил техническую терминологию и акценты на ключевых преимуществах, чтобы оно солидно смотрелось на GitHub или в документации.

---

# 🛠 Radmin Book Manager (Ultimate Editor & Launcher)

**Radmin Book Manager** is a specialized Python-based application (PyQt6) designed for advanced management of Radmin Viewer address books (`.rpb` files). The tool combines low-level binary data editing capabilities with a user-friendly graphical interface tailored for the daily workflows of system administrators.

### 🌟 Purpose
The application addresses the limitations of the proprietary `.rpb` format, enabling users to edit, import, and automate connections that typically require manual configuration in the standard Radmin Viewer.

---

### 🚀 Key Features

#### 1. Binary File Management (.rpb)
* **Deep Parsing:** Comprehensive analysis of RPB segments (6138 bytes each) to extract record names, IP addresses, ports, logins, and domain names.
* **Database Reconstruction:** Recursive assembly of folder structures and hosts back into binary format. It includes automatic recalculation of internal IDs (`RecordID`, `ParentID`), ensuring full compatibility with the official Radmin Viewer.

#### 2. Intelligent Password Management
* **Local JSON Storage:** Since Radmin encrypts passwords within the `.rpb` file, this app utilizes a parallel `radmin_credentials.json` database. This allows passwords to be "re-linked" to records even after they are moved, renamed, or recreated.
* **Seamless Integration:** Passwords are automatically saved and updated during table editing.

#### 3. Connection Automation (AutoFill)
* **One-Click Launch:** Launch Radmin Viewer directly from the interface in various modes: Full Control, View Only, Telnet, or File Transfer.
* **Form Auto-Completion:** A unique feature utilizing WinAPI to detect Radmin or Windows authentication windows. The app automatically injects the login and password, simulating an "Enter" keypress, eliminating manual credential entry.

#### 4. Data Flexibility & Migration
* **CSV Import/Export:** Mass-load host lists from Excel/CSV or export the current address book for reporting and auditing.
* **Drag-and-Drop Interface:** Easily reorganize your network structure by moving hosts between folders within the tree view.

#### 5. Technical Monitoring
* **Built-in Logger:** An integrated console window provides real-time feedback on file parsing status, window handle searches, and automation results.

---

### 💻 Technology Stack
* **Language:** Python 3.
* **GUI:** PyQt6 (providing a modern look and high performance).
* **System Interaction:** `ctypes` (WinAPI) for window handle detection and authentication process management.
* **Binary Processing:** `struct` module for handling C-style data structures.

---

### 💡 Why use this over the standard Viewer?
1.  **Bulk Editing:** Unlike the standard Viewer, you can change ports or domains for 50+ servers at once via CSV.
2.  **Transparency:** Access hidden technical fields and debug your address book's internal tree structure.
3.  **Efficiency:** The AutoFill feature saves hours of manual labor when managing large-scale server environments.

---

### 📚 Credits & Acknowledgments
This project utilizes logic and research from the following repositories:
* [xjj0906/RadminSavePassword](https://github.com/xjj0906/RadminSavePassword)
* [kuzyara/Import-export-radmin-book-1C](https://github.com/kuzyara/Import-export-radmin-book-1C)

---

**Does this version work for you? If you're planning to post this on GitHub, I could also help you write a "Getting Started" section with installation steps.** 😊
