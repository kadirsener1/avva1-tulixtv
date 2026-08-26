#!/usr/bin/env python3

import requests
import json
import re
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed


TOTAL = 1000
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
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=8
        )

        if r.status_code != 200:
            return None

        if "HlsStreamURL" not in r.text:
            return None

        text = r.text

        stream_url = None

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        last_isvod = None

        for i, line in enumerate(lines):

            if line == "isVOD" and i + 1 < len(lines):
                last_isvod = lines[i + 1].lower()

            if line == "HlsStreamURL" and i + 1 < len(lines):

                possible_url = lines[i + 1]

                if (
                    possible_url.startswith("http")
                    and last_isvod == "false"
                ):
                    stream_url = possible_url
                    break

        # XML formatı için yedek kontrol
        if not stream_url:

            match = re.search(
                r"<key>\s*isVOD\s*</key>"
                r"\s*<string>\s*false\s*</string>"
                r".*?"
                r"<key>\s*HlsStreamURL\s*</key>"
                r"\s*<string>(.*?)</string>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                stream_url = match.group(1).strip()

        if not stream_url:
            return None

        stream_url = unescape(stream_url)
        stream_url = stream_url.replace("\\/", "/").strip()

        # Domain filtresi
        if ALLOWED_DOMAIN not in stream_url:
            return None

        # Kanal adını bul
        name = None

        for i, line in enumerate(lines):

            if (
                line == "name"
                and i + 1 < len(lines)
                and not lines[i + 1].startswith("http")
            ):
                name = lines[i + 1]
                name = name.replace(" - Live", "").strip()
                break

        # XML üzerinden kanal adı
        if not name:

            match = re.search(
                r"<key>\s*name\s*</key>"
                r"\s*<string>(.*?)</string>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                name = match.group(1).strip()

        if not name:
            name = f"Kanal {ch_id}"

        name = unescape(name)
        name = name.replace(" - Live", "").strip()

        # Logo adresini bul
        logo = None

        for i, line in enumerate(lines):

            if (
                line == "logoUrlHD"
                and i + 1 < len(lines)
                and lines[i + 1].startswith("http")
            ):
                logo = lines[i + 1]
                break

        # XML üzerinden logo bul
        if not logo:

            match = re.search(
                r"<key>\s*logoUrlHD\s*</key>"
                r"\s*<string>(.*?)</string>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                logo = match.group(1).strip()

        if not logo:
            logo = (
                f"https://www.giniko.com/logos/190x110/"
                f"{ch_id}.jpg"
            )

        logo = unescape(logo).strip()

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

    if value is None:
        return ""

    return (
        str(value)
        .replace('"', "'")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def create_m3u_from_json():

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            channels = json.load(f)

    except Exception as error:
        print(f"JSON okunamadı: {error}")
        return

    print(f"JSON içindeki kayıt sayısı: {len(channels)}")

    added_count = 0

    try:

        with open(M3U_FILE, "w", encoding="utf-8", newline="\n") as f:

            # M3U dosya başlığı
            f.write("#EXTM3U\n")

            for channel in channels:

                channel_id = clean_m3u_value(
                    channel.get("id")
                )

                channel_name = clean_m3u_value(
                    channel.get("name")
                )

                logo_url = clean_m3u_value(
                    channel.get("logo")
                )

                stream_url = clean_m3u_value(
                    channel.get("stream")
                )

                if not stream_url:
                    print(
                        f"Stream bulunamadı, atlandı: "
                        f"{channel_name or channel_id}"
                    )
                    continue

                if not channel_name:
                    channel_name = f"Kanal {channel_id}"

                # Kanal bilgisi ve logo
                f.write(
                    f'#EXTINF:-1 '
                    f'tvg-id="{channel_id}" '
                    f'tvg-name="{channel_name}" '
                    f'tvg-logo="{logo_url}",'
                    f'{channel_name}\n'
                )

                # Yayın adresi
                f.write(stream_url + "\n")

                added_count += 1

    except Exception as error:
        print(f"M3U yazılamadı: {error}")
        return

    print(f"M3U dosyası oluşturuldu: {M3U_FILE}")
    print(f"M3U içine eklenen kanal sayısı: {added_count}")


def main():

    print(f"Tarama başlıyor: 1-{TOTAL}")

    results = []

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(check_channel, i): i
            for i in range(1, TOTAL + 1)
        }

        done = 0

        for future in as_completed(futures):

            done += 1

            try:
                result = future.result()

                if result:
                    results.append(result)

            except Exception:
                pass

            if done % 50 == 0:
                print(
                    f"[{done}/{TOTAL}] "
                    f"Bulunan: {len(results)} kanal"
                )

    # Kanal ID'sine göre sırala
    results.sort(key=lambda x: x["id"])

    # JSON dosyasını oluştur
    try:

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(
                results,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(f"JSON dosyası oluşturuldu: {JSON_FILE}")

    except Exception as error:
        print(f"JSON yazılamadı: {error}")
        return

    # JSON içinden M3U oluştur
    create_m3u_from_json()

    print()
    print(f"Toplam {len(results)} kanal bulundu")


if __name__ == "__main__":
    main()
