<div align="center">
  <h1>⚡ StreamBoost 2.0</h1>
  <p><b>The Ultimate Open-Source PC Optimizer & Process Manager for Streamers and Gamers.</b></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
  [![Python version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
  [![Platform: Windows](https://img.shields.io/badge/Platform-Windows-cyan.svg)](#)
  
  Made with ❤️ by <b><a href="https://github.com/HunterisLive-1">HunterisLive</a></b>
</div>

<hr>

## 📖 Overview

**StreamBoost** is a lightweight, aggressive, and highly-configurable performance enhancement utility engineered directly for the background management of your Windows PC. It is specifically designed to flush unnecessary system loads, kill background bloatware securely, and allocate native hardware resources unconditionally towards active gaming or streaming software.

---

## 🚀 Core Features

| Feature | Description |
| :--- | :--- |
| **📊 Real-Time Telemetry** | A dynamic dashboard mapping live CPU and continuous RAM payload utilization. |
| **⚙️ Advanced Process Manager** | Deeply inspect background tasks. Setup absolute Whitelists (`Stream Mode`, `Game Mode`) while terminating unauthorized background bleeding. |
| **💾 Low-Level RAM Optimizer** | Directly targets Windows OS APIs (`EmptyWorkingSet`) to instantly flush standby Memory caches and liberate hard-locked RAM safely. |
| **🧹 Deep System Cleanup** | Native directory sweeps mapping directly inside `%TEMP%` and `Prefetch` arrays for clearing out Windows clutter. |
| **🎛️ Silent Background Routing** | Designed using native `pystray` architecture for hiding cleanly inside the System Taskbar. |

---

## 🛠️ Prerequisites

To run this application natively, ensure your environment maintains the following configurations:

- **OS:** Windows 10 / 11
- **Engine:** Python 3.10+ installed and exposed to System `PATH`
- **Privileges:** Administrator status (Highly Recommended for native RAM hooks and Temp overrides)

---

## 💻 Installation & Usage

Follow these exact steps to initialize the core script onto your machine natively without building.

1. **Clone the Repository**
   ```bash
   git clone https://github.com/HunterisLive-1/StreamBoost.git
   cd StreamBoost
   ```

2. **Install Core Dependencies**
   It is recommended to run this within a Virtual Environment, although it works globally as well.
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute the Engine**
   Launch StreamBoost directly. Run your Command Prompt (CMD) or Powershell as **Administrator** for complete optimization access!
   ```bash
   python streamboost.py
   ```

> [!TIP]
> **Pro-Tip**: Head over to the **Settings** tab within the application and enable `"Minimize to System Tray on close"`. This will maintain aggressive background clearing phases autonomously!

---

## 📜 Legal & License
This project operates entirely Open-Sourced.
