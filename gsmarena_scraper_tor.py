import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import time
import csv
import os

# ====== Tor Config ======
TOR_PROXY = 'socks5h://127.0.0.1:9050'
TOR_CONTROL_PORT = 9051
TOR_PASSWORD = ''  # no password by default

# ====== CSV Config ======
CSV_FILE = 'gsmarena_filled.csv'
FIELDS = [
    "URL", "Name", "Network - Technology", "Launch - Announced", "Launch - Status",
    "Body - Dimensions", "Body - Weight", "Body - SIM", "Display - Type", "Display - Size",
    "Display - Resolution", "Platform - OS", "Platform - Chipset", "Platform - CPU", "Platform - GPU",
    "Memory - Card slot", "Memory - Internal", "Main Camera - Single", "Main Camera - Video",
    "Selfie camera - Single", "Selfie camera - Video", "Sound - Loudspeaker", "Sound - 3.5mm jack",
    "Comms - WLAN", "Comms - Bluetooth", "Comms - Positioning", "Comms - NFC", "Comms - Radio",
    "Comms - USB", "Features - Sensors", "Battery - Type", "Battery - Talk time", "Battery - Music play",
    "Misc - Colors", "Misc - Models", "SAR EU", "Price"
]

# ====== Tor IP Rotation ======
def renew_tor_ip():
    print("🔄 Tor IP renewed. Waiting for new circuit...")
    with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
        controller.authenticate(password=TOR_PASSWORD)
        controller.signal(Signal.NEWNYM)
    time.sleep(8)

# ====== Load URLs from File ======
def load_urls_from_csv(input_file):
    """Load URLs from a file with one URL per line."""
    urls = []
    with open(input_file, newline='', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if url:
                # Extract name from URL, like 'acer_betouch_e400' → 'Acer beTouch E400'
                name_part = url.split("/")[-1].replace(".php", "")
                name = " ".join(part.capitalize() for part in name_part.split("_"))
                urls.append((url, name))
    return urls


# ====== Save a Row Immediately ======
def append_row(row):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ====== Scrape a Single Phone Page ======
def scrape_phone(url, name):
    print(f"🔍 Scraping: {name} - {url}")
    proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(5):
        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=15)
            if response.status_code == 429:
                print(f"⚠ 429 Too Many Requests received, renewing Tor IP and waiting...")
                renew_tor_ip()
                continue
            response.raise_for_status()
            return parse_specs(response.text, url, name)
        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            renew_tor_ip()
    return None

# ====== Parse the Specs ======
def parse_specs(html, url, name):
    soup = BeautifulSoup(html, 'html.parser')
    spec_dict = {field: 'Unknown' for field in FIELDS}
    spec_dict["URL"] = url
    spec_dict["Name"] = name

    # Scrape from specs-list as before
    specs_div = soup.find("div", {"id": "specs-list"})
    if specs_div:
        for table in specs_div.find_all("table"):
            category = table.find("th").text.strip() if table.find("th") else "Unknown"
            for row in table.find_all("tr"):
                ttl = row.find("td", {"class": "ttl"})
                nfo = row.find("td", {"class": "nfo"})
                if ttl and nfo:
                    label = ttl.text.strip()
                    value = nfo.text.strip()
                    key = f"{category} - {label}"
                    if key in FIELDS:
                        spec_dict[key] = value

    # ✅ Explicitly extract the Price
    price_tag = soup.find("td", {"data-spec": "price"})
    if price_tag:
        spec_dict["Price"] = price_tag.text.strip()

    return spec_dict

# ====== Main Function ======
def main():
    input_file = 'phones_urls.csv'
    phone_list = load_urls_from_csv(input_file)
    print(f"📦 Total phones to scrape: {len(phone_list)}")

    for url, name in phone_list:
        result = scrape_phone(url, name)
        if result:
            append_row(result)
        else:
            print(f"❌ Skipped (Failed): {name} - {url}")

    print(f"\n🏁 Finished. Output saved to '{CSV_FILE}'")

if __name__ == "__main__":
    main()

