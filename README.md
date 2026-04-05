# ⚡ StreamBoost 2.0

**StreamBoost** is a powerful, open-source PC optimization and process management tool designed for Streamers and Gamers to instantly eliminate background bloatware and maximize system performance.

Made with ❤️ by **[HunterisLive](https://github.com/HunterisLive-1)**

## 🚀 Features
- **Dashboard:** Real-time RAM and CPU monitoring.
- **Process Manager:** Safely whitelist essential apps while killing unnecessary background processes.
- **RAM Optimizer:** Instantly flushes standby RAM using Windows APIs (`EmptyWorkingSet`).
- **Junk Cleanup:** Clean Windows Temp, Prefetch, and unneeded cache files.
- **Profiles:** Switch easily between Stream Mode and Gaming Mode.
- **System Tray:** Hide seamlessly in the tray while playing.

## 🛠 Prerequisites

Make sure you have Python 3.10+ installed.

```bash
pip install -r requirements.txt
```

## 🎮 How to Build Your Own EXE

Run the `build.bat` script provided.

```bash
.\build.bat
```
This handles PyInstaller automatically and puts your `StreamBoost.exe` in the `dist/` folder.

## 📜 License
MIT License
