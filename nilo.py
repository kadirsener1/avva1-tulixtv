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


def normalize_url(value):
    """
    URL şu formatta gelirse:

    [https://site.com/logo.jpg](https://site.com/logo.jpg)

    sadece gerçek URL kısmını alır.
    """

    if not value:
        return ""

    value = unescape(str(value)).strip()

    # Metin içinde bulunan tüm URL'leri bul
    urls = re.findall(
        r"https?://[^)\s<>'\"]+",
        value
    )

    if urls:
        # Markdown bağlantısında genellikle son URL gerçek hedef URL'dir
        return urls[-1].strip()

    return value


def clean_m3u_value(value):
    """
    M3U kanal adı ve attribute değerlerini temizler.
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

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        last_isvod = None

        # Satır satır stream bul
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

        # XML formatı için yedek stream araması
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

        # Markdown veya XML karakterlerini temizle
        stream_url = normalize_url(stream_url)

        if not stream_url:
            return None

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
                break

        # XML içinden kanal adı bul
        if not name:

            match = re.search(
                r"<key>\s*name\s*</key>"
                r"\s*<string>(.*?)</string>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                name = match.group(1)

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

        # XML içinden logo bul
        if not logo:

            match = re.search(
                r"<key>\s*logoUrlHD\s*</key>"
                r"\s*<string>(.*?)</string>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:
                logo = match.group(1)

        if not logo:
            logo = (
                f"https://www.giniko.com/logos/190x110/"
                f"{ch_id}.jpg"
            )

        # Markdown logo bağlantısını temizle
        logo = normalize_url(logo)

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


def create_m3u_from_json():

    try:

        with open(JSON_FILE, "r", encoding="utf-8") as file:
            channels = json.load(file)

    except Exception as error:
        print(f"JSON dosyası okunamadı: {error}")
        return

    print(f"JSON içindeki kanal sayısı: {len(channels)}")

    added_count = 0

    try:

        with open(
            M3U_FILE,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as file:

            # M3U başlığı
            file.write("#EXTM3U\n")

            for channel in channels:

                channel_id = clean_m3u_value(
                    channel.get("id")
                )

                channel_name = clean_m3u_value(
                    channel.get("name")
                )

                # JSON'daki Markdown logo linkini temizle
                logo_url = normalize_url(
                    channel.get("logo")
                )

                logo_url = clean_m3u_value(logo_url)

                # JSON'daki Markdown stream linkini temizle
                stream_url = normalize_url(
                    channel.get("stream")
                )

                stream_url = stream_url.strip()

                if not stream_url:
                    print(
                        f"Stream yok, atlandı: "
                        f"{channel_name or channel_id}"
                    )
                    continue

                if not channel_name:
                    channel_name = f"Kanal {channel_id}"

                # M3U kanal bilgisi
                file.write(
                    f'#EXTINF:-1 '
                    f'tvg-id="{channel_id}" '
                    f'tvg-name="{channel_name}" '
                    f'tvg-logo="{logo_url}",'
                    f'{channel_name}\n'
                )

                # Gerçek stream adresi
                file.write(stream_url + "\n")

                added_count += 1

    except Exception as error:
        print(f"M3U dosyası oluşturulamadı: {error}")
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

    # Kanal ID'sine göre sırala
    results.sort(key=lambda item: item["id"])

    # JSON dosyasını kaydet
    try:

        with open(JSON_FILE, "w", encoding="utf-8") as file:
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

    # JSON dosyasından M3U oluştur
    create_m3u_from_json()

    print()
    print(f"Toplam {len(results)} kanal bulundu")


if __name__ == "__main__":
    main()
