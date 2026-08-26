#!/usr/bin/env python3

import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

TOTAL = 2000
WORKERS = 30

JSON_FILE = "channels5.json"
M3U_FILE = "channels5.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.ginikoturkish.com/"
}

ALLOWED_DOMAIN = "trn03.tulix.tv"


def check_channel(ch_id):

    url = f"https://ginikoturkish.com/xml/secure/plist.php?ch={ch_id}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=8)

        if r.status_code != 200 or "HlsStreamURL" not in r.text:
            return None

        text = r.text
        stream_url = None

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        last_isvod = None

        for i, line in enumerate(lines):

            if line == "isVOD" and i + 1 < len(lines):
                last_isvod = lines[i + 1]

            if line == "HlsStreamURL" and i + 1 < len(lines):
                u = lines[i + 1]

                if u.startswith("http") and last_isvod == "false":
                    stream_url = u
                    break

        if not stream_url:
            m = re.search(
                r"<key>isVOD</key>\s*<string>false</string>.*?"
                r"<key>HlsStreamURL</key>\s*<string>(.*?)</string>",
                text,
                re.DOTALL
            )

            if m:
                stream_url = m.group(1)

        if not stream_url:
            return None

        # Domain filtresi
        if ALLOWED_DOMAIN not in stream_url:
            return None

        # Kanal adı
        name = None

        for i, line in enumerate(lines):
            if (
                line == "name"
                and i + 1 < len(lines)
                and not lines[i + 1].startswith("http")
            ):
                name = lines[i + 1].replace(" - Live", "").strip()
                break

        if not name:
            m = re.search(
                r"<key>name</key>\s*<string>(.*?)</string>",
                text
            )

            name = (
                m.group(1).replace(" - Live", "").strip()
                if m
                else f"Kanal {ch_id}"
            )

        # Logo
        logo = None

        for i, line in enumerate(lines):
            if (
                line == "logoUrlHD"
                and i + 1 < len(lines)
                and lines[i + 1].startswith("http")
            ):
                logo = lines[i + 1]
                break

        if not logo:
            m = re.search(
                r"<key>logoUrlHD</key>\s*<string>(.*?)</string>",
                text
            )

            logo = (
                m.group(1)
                if m
                else f"https://www.giniko.com/logos/190x110/{ch_id}.jpg"
            )

        print(f"✓ {ch_id}: {name}")

        return {
            "id": ch_id,
            "name": name,
            "logo": logo,
            "stream": stream_url,
            "xmlUrl": url
        }

    except Exception:
        return None


def clean_m3u_value(value):
    """
    M3U içindeki attribute değerlerinde sorun çıkarabilecek
    tırnak ve satır sonlarını temizler.
    """
    if value is None:
        return ""

    return (
        str(value)
        .replace('"', "'")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def create_m3u(results):
    """
    channels5.json içinde bulunan kanallardan M3U dosyası oluşturur.
    """

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for channel in results:
            channel_id = clean_m3u_value(channel.get("id"))
            name = clean_m3u_value(channel.get("name"))
            logo = clean_m3u_value(channel.get("logo"))
            stream = str(channel.get("stream", "")).strip()

            if not stream:
                continue

            if not name:
                name = f"Kanal {channel_id}"

            f.write(
                f'#EXTINF:-1 '
                f'tvg-id="{channel_id}" '
                f'tvg-name="{name}" '
                f'tvg-logo="{logo}" '
                f'group-title="Giniko",'
                f'{name}\n'
            )

            f.write(f"{stream}\n")

    print(f"M3U dosyası oluşturuldu: {M3U_FILE}")


def main():

    print(f"Tarama başlıyor: 1-{TOTAL}")

    results = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:

        futures = {
            executor.submit(check_channel, i): i
            for i in range(1, TOTAL + 1)
        }

        done = 0

        for future in as_completed(futures):

            done += 1

            result = future.result()

            if result:
                results.append(result)

            if done % 50 == 0:
                print(
                    f"[{done}/{TOTAL}] "
                    f"Bulunan: {len(results)} kanal"
                )

    results.sort(key=lambda x: x["id"])

    # JSON dosyasını kaydet
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"JSON dosyası oluşturuldu: {JSON_FILE}")

    # M3U dosyasını oluştur
    create_m3u(results)

    print(f"\nToplam {len(results)} kanal bulundu")


if __name__ == "__main__":
    main()
