# NetVault — Network Router Configuration Store

## Project Description

**NetVault** is a desktop application built using **Python, Tkinter, and SQLite** to manage network router configurations with built-in version control support. 
It allows network administrators and students to securely organize multiple configuration states (Startup, Running, and Golden Templates), track changes using visual diffs, and maintain local backups in a structured SQLite database.

---

## Features

* **Router Management:** Add, edit, and delete network router profiles.
* **Version Control:** Store and manage multiple configuration versions (Startup, Running, and Golden Template).
* **Import & Export:** Import configurations directly from `.cfg` or `.txt` files and export backups locally.
* **Configuration Diff:** Compare different configuration versions side-by-side using `difflib`.
* **Quick Search:** Search routers by Hostname, IP Address, Vendor, or Location.
* **Demo Ready:** Includes pre-loaded sample data for instant testing and demonstration.

---

## Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.8+** | Core programming language |
| **Tkinter** | Graphical User Interface (GUI) |
| **SQLite** | Local relational database storage |
| **difflib** | Configuration version comparison |

---

## How to Run

1. Clone the repository or download the project files.
2. Ensure **Python 3.8 or higher** is installed on your system.
3. Open a terminal or command prompt inside the project folder.
4. Run the application:
   ```bash
   python netvault.py
   ```

---

## Team Members

1. **Md Sikandar** — `BWU/BTA/25/563`
2. **Shivam Kumar** — `BWU/BTA/25/554`
3. **Sunrise Sk** — `BWU/BTA/25/555`
4. **Samima Nasrin** — `BWU/BTA/25/572`
