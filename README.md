# Cesbo-Astra-Monitoring-Control-Telegram-Bot
A lightweight Python bot designed to monitor and manage streams in Cesbo Astra. It provides real-time alerts and a user-friendly interface to manage your headend directly from Telegram.
🚀 Features
Real-time Alerts: Notifies you instantly if a stream goes down (with a 30-second anti-spam delay).

Group Management: Automatically categorizes streams based on your Astra groups.

Stream Control: Restart or Toggle (On/Off) streams via inline buttons.

Detailed Stats: View bitrate, CC errors, and PES errors for each stream.

Access Control: Whitelist system to ensure only authorized users can control the bot.

🛠 Installation
Clone the repository:

Bash
git clone https://github.com/madadmin2/astra-telegram-bot.git
cd astra-telegram-bot
Install dependencies:

Bash
pip install pyTelegramBotAPI requests
Edit bot.py and fill in your:

API_TOKEN (from @BotFather)

ASTRA_URL (e.g., http://1.2.3.4:8000)

ASTRA_AUTH (username and password)

WHITELIST (your Telegram User ID)

Run the bot:

Bash
python3 bot.py

## Support the Project 🍺

If this bot helps you manage your streams and you'd like to support my work, you can buy me a beer here:

* [💸 Support via Revolut](https://revolut.me/iliyapereshki)
* [🅿️ Support via PayPal](https://paypal.me/iliapereshki)
