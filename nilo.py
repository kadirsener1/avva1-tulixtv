#!/usr/bin/env python3

import json
import re
from html import unescape
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


# Ayarlar
TOTAL = 1000
WORKERS = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.ginikoturkish.com/"
}

ALLOWED_DOMAIN = "trn03.tulix.tv"


# Dosyaları Python dosyasının bulunduğu klasöre kaydet
BASE_DIR = Path(__file__).resolve().parent

JSON_FILE = BASE_DIR / "channels5.json"
M3U_FILE = BASE_DIR / "channels5.m3u"


def get_plist_value(text, key):
    """
    XML içindeki şu yapıyı okur:

    <key>name</key>
    <string>Kanal Adı</string>
    """

    pattern = (
        rf"<key>\s*{re.escape(key)}\s*</key>"
        rf"\s*<string>(.*?)</string>"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return unescape(match.group(1)).strip()

    return None


def check_channel(ch_id):

    url = (
        f"https://ginikoturkish.com/xml/secure/plist.php"
        f"?ch={ch_id}"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=8
        )

        if response.status_code != 200:
            return None

        text = response.text

        if "HlsStreamURL" not in text:
            return None

        stream_url = None

        # Önce mevcut satır yapısıyla kontrol et
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

            pattern = (
                r"<key>\s*isVOD\s*</key>"
                r"\s*<string>\s*false\s*</string>"
                r".*?"
                r"<key>\s*HlsStreamURL\s*</key>"
                r"\s*<string>(.*?)</string>"
            )

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                stream_url = match.group(1).strip()

        if not stream_url:
            return None

        stream_url = unescape(stream_url.strip())

        # Domain filtresi
        if ALLOWED_DOMAIN not in stream_url:
            return None

        # Kanal adını al
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

        if not name:
            name = get_plist_value(text, "name")

        if not name:
            name = f"Kanal {ch_id}"

        name = unescape(name).replace(" - Live", "").strip()

        # Logo adresini al
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
            logo = get_plist_value(text, "logoUrlHD")

        if not logo:
            logo = (
                f"https://www.giniko.com/logos/190x110/"
                f"{ch_id}.jpg"
            )

        logo = unescape(logo.strip())

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
    M3U attribute değerlerinde sorun çıkarabilecek
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


def create_m3u_from_json():
    """
    channels5.json dosyasını okuyarak channels5.m3u oluşturur.
    """

    if not JSON_FILE.exists():
        print(f"JSON dosyası bulunamadı: {JSON_FILE}")
        return

    try:
        with JSON_FILE.open("r", encoding="utf-8") as file:
            channels = json.load(file)

    except Exception as error:
        print(f"JSON dosyası okunamadı: {error}")
        return

    channel_count = 0

    try:
        with M3U_FILE.open(
            "w",
            encoding="utf-8",
            newline="\n"
        ) as file:

            file.write("#EXTM3U\n")

            for channel in channels:

                channel_id = clean_m3u_value(
                    channel.get("id")
                )

                name = clean_m3u_value(
                    channel.get("name")
                )

                logo = clean_m3u_value(
                    channel.get("logo")
                )

                stream = str(
                    channel.get("stream", "")
                ).strip()

                if not stream:
                    continue

                if not name:
                    name = f"Kanal {channel_id}"

                # M3U kanal bilgisi
                file.write(
                    f'#EXTINF:-1 '
                    f'tvg-id="{channel_id}" '
                    f'tvg-name="{name}" '
                    f'tvg-logo="{logo}" '
                    f'group-title="Giniko",'
                    f'{name}\n'
                )

                # Yayın adresi
                file.write(stream + "\n")

                channel_count += 1

    except Exception as error:
        print(f"M3U dosyası oluşturulamadı: {error}")
        return

    print(f"M3U dosyası oluşturuldu: {M3U_FILE}")
    print(f"M3U içindeki kanal sayısı: {channel_count}")


def main():

    print(f"Tarama başlıyor: 1-{TOTAL}")
    print(f"Çalışma klasörü: {BASE_DIR}")

    results = []

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(check_channel, channel_id): channel_id
            for channel_id in range(1, TOTAL + 1)
        }

        completed = 0

        for future in as_completed(futures):

            completed += 1

            try:
                result = future.result()

                if result:
                    results.append(result)

            except Exception:
                pass

            if completed % 50 == 0:
                print(
                    f"[{completed}/{TOTAL}] "
                    f"Bulunan: {len(results)} kanal"
                )

    # Kanal numarasına göre sırala
    results.sort(key=lambda item: item["id"])

    # JSON dosyasını kaydet
    try:
        with JSON_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                results,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(f"JSON dosyası oluşturuldu: {JSON_FILE}")

    except Exception as error:
        print(f"JSON dosyası oluşturulamadı: {error}")
        return

    # JSON içinden M3U oluştur
    create_m3u_from_json()

    print(f"\nToplam {len(results)} kanal bulundu")


if __name__ == "__main__":
    main()
