import os
import requests

webhook = os.getenv("DISCORD_WEBHOOK")

# Example data (replace with your real HR logic if needed)
message = "**🔥 HR PICKS TODAY 🔥**\n\n"
message += "Aaron Judge - 28%\n"
message += "Corey Seager - 20.8%\n"
message += "Rafael Devers - 15.6%\n"
message += "Fernando Tatis Jr. - 15.3%\n"

print(message)

# Send to Discord if webhook exists
if webhook:
    try:
        requests.post(webhook, json={"content": message})
        print("✅ Sent to Discord")
    except Exception as e:
        print("❌ Discord error:", e)
else:
    print("⚠️ No webhook found, skipping Discord (but script still works)")
