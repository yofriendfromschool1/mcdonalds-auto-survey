<div align="center">

# 🍔 McDVOICE Auto Survey Bot

**Automatically complete the McDonald's customer satisfaction survey and get your validation code in seconds.**

⚠️ **For educational purposes only. Not affiliated with McDonald's Corporation.** ⚠️

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Dual Entry Modes** | Enter a 26-digit receipt code **or** use store info to auto-generate surveys |
| 🤖 **Smart Brute-Force Solver** | Handles dynamic survey pages with smart element detection |
| 📷 **QR Code Scanner** | Scan your receipt barcode directly from your phone camera |
| 🌐 **Web UI** | Beautiful, responsive web interface — no command line needed |
| 💻 **CLI Mode** | Full command-line interface for power users |
| 📊 **Weighted Answers** | Realistic answer distribution (biased positive) to avoid detection |
| 💬 **Review Pool** | 50+ prewritten reviews for the comment section |
| 📜 **History Tracking** | All validation codes saved locally and to `results.json` |
| ⚡ **Headless Chrome** | Runs silently in the background, no browser window needed |
| 📋 **One-Click Copy** | Copy your validation code to clipboard instantly |

## 📸 How It Works

```
Receipt Code → Bot fills survey → Smart solver clicks through pages → Validation Code! 🎉
```

1. **You** provide a receipt code (scan QR or type it in)
2. **Bot** navigates to mcdvoice.com and enters your code
3. **Smart solver** detects and answers each survey page automatically
4. **Validation code** is extracted and displayed to you

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Google Chrome** browser installed
- **ChromeDriver** (auto-installed via `webdriver-manager`)

### Installation

```bash
# Clone the repo
git clone https://github.com/yofriendfromschool1/mcdonalds-auto-survey.git
cd mcdonalds-auto-survey

# Install dependencies
pip install -r requirements.txt
```

### Option 1: Web UI (Recommended)

```bash
# Start the web server
python server.py

# Open in your browser
# http://localhost:5000
```

Then:
1. Enter your 26-digit receipt code (or scan the QR code on your receipt)
2. Click **Start Survey**
3. Watch the progress bar
4. Copy your validation code! 🎉

### Option 2: Command Line

```bash
python auto_survey.py
```

Follow the interactive prompts to choose your entry mode and start the survey.

---

## 📂 Project Structure

```
mcdonalds-auto-survey/
├── auto_survey.py       # 🤖 Core survey bot (Selenium)
├── server.py            # 🌐 Flask web server + API
├── reviews.json         # 💬 Review pool for survey comments
├── requirements.txt     # 📦 Python dependencies
├── results.json         # 📜 Saved validation codes (auto-created)
├── README.md            # 📖 This file
└── static/
    ├── index.html       # 🎨 Web UI page
    ├── style.css        # 💅 Premium dark theme styles
    └── app.js           # ⚡ Frontend logic + QR scanner
```

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   Web Browser   │────▶│  Flask API   │────▶│  Selenium    │
│   (Frontend)    │◀────│  (server.py) │◀────│  Chrome Bot  │
│                 │     │              │     │  (headless)  │
│  - QR Scanner   │     │  - /api/     │     │              │
│  - Code Input   │     │    survey    │     │  - Navigate  │
│  - Progress     │     │  - /api/     │     │  - Fill form │
│  - History      │     │    status    │     │  - Solve Q's │
└─────────────────┘     └──────────────┘     └──────────────┘
```

## 🔧 Configuration

### Receipt Code Format
The receipt code on your McDonald's receipt looks like:
```
XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-X
```
Each segment is separated by dashes. Enter each segment into the corresponding field, or paste the whole code at once.

### Store Info Mode
If you don't have a receipt code, you can use Store Info mode:
- **Store Number**: The 5-digit McDonald's store number
- **Register/KS Number**: The register number (usually 01-10)

The bot will auto-generate realistic transaction data (date, time, transaction number, amount).

---

## ⚠️ Disclaimer

- This tool is created **purely for educational purposes** to understand web automation
- It is **not intended** to falsely obtain free food or manipulate satisfaction scores
- **No warranty** is provided — use at your own risk
- The survey site may have anti-bot protections that prevent automation
- McDonald's may update their survey site at any time, which could break this tool
- Any misuse is strictly against the intended purpose of this project

## 🤝 Credits

This project combines and improves upon techniques from:
- [happymeal](https://github.com/ForgedCore8/happymeal) by ForgedCore8
- [mcd-voice-bot](https://github.com/NDBNeer/mcd-voice-bot) by Noah Broyles
- [Mcdonalds-Survey-Automation](https://github.com/vishrantgupta/Mcdonalds-Survey-Automation) by vishrantgupta

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
