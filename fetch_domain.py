import requests
from bs4 import BeautifulSoup
import re

def main():
    target_url = "https://amp-3d92fe5184.selcuksportshdamp-aa805a079c.click/amp.html"
    proxy_url = "https://api.codetabs.com/v1/proxy/?quest="
    
    html_content = None
    
    try:
        response = requests.get(target_url, timeout=10)
        response.raise_for_status()
        html_content = response.text
        print("Normal bağlantı başarılı")
    except:
        try:
            response = requests.get(f"{proxy_url}{target_url}", timeout=10)
            response.raise_for_status()
            html_content = response.text
            print("Proxy bağlantısı başarılı")
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            return
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Yöntem: Class'a göre div içindeki linkleri al
        target_div = soup.find('div', class_='mobile-button-container mobile')
        domains = {}
        
        if target_div:
            links = target_div.find_all('a', href=True)
            print(f"Hedef div içinde {len(links)} link bulundu")
            
            # İstenen sıraya göre domainleri al
            if len(links) >= 1:
                domains['selcuk_guncel_domain'] = links[0]['href']
            if len(links) >= 2:
                domains['xyzsports_guncel_domain'] = links[1]['href']
            if len(links) >= 3:  # 4. sıradaki domain (index 3)
                domains['dizilife_guncel_domain'] = links[2]['href']
            if len(links) >= 5:
                domains['sporcafe_guncel_domain'] = links[4]['href']
        
        # 2. Yöntem: Anahtar kelimelere göre regex ile arama
        html_text = str(soup)
        
        # SelcukSports için regex
        selcuk_pattern = r'https?://[^"\']*selcuksports[^"\']*'
        selcuk_matches = re.findall(selcuk_pattern, html_text, re.IGNORECASE)
        if selcuk_matches and 'selcuk_guncel_domain' not in domains:
            domains['selcuk_guncel_domain'] = selcuk_matches[0]
        
        # XYZSports için regex
        xyz_pattern = r'https?://[^"\']*xyzsports[^"\']*'
        xyz_matches = re.findall(xyz_pattern, html_text, re.IGNORECASE)
        if xyz_matches and 'xyzsports_guncel_domain' not in domains:
            domains['xyzsports_guncel_domain'] = xyz_matches[0]
        
        # Dizilife için regex (dizi19 anahtar kelimesi)
        dizilife_pattern = r'https?://[^"\']*dizi19[^"\']*'
        dizilife_matches = re.findall(dizilife_pattern, html_text, re.IGNORECASE)
        if dizilife_matches and 'dizilife_guncel_domain' not in domains:
            domains['dizilife_guncel_domain'] = dizilife_matches[0]
        
        # SporCafe için regex
        sporcafe_pattern = r'https?://[^"\']*sporcafe[^"\']*'
        sporcafe_matches = re.findall(sporcafe_pattern, html_text, re.IGNORECASE)
        if sporcafe_matches and 'sporcafe_guncel_domain' not in domains:
            domains['sporcafe_guncel_domain'] = sporcafe_matches[0]
        
        # Domainleri temizle ve formatla
        for key in domains:
            domain = domains[key]
            if domain.startswith('//'):
                domains[key] = 'https:' + domain
            elif not domain.startswith('http'):
                domains[key] = 'https://' + domain
        
        # Dosyaya yaz
        with open('selcuk_sports_guncel_domain.txt', 'w', encoding='utf-8') as f:
            for name, url in domains.items():
                f.write(f"{name}={url}\n")
        
        print("Domainler başarıyla yazıldı:")
        for name, url in domains.items():
            print(f"{name}: {url}")
            
    except Exception as e:
        print(f"Hata: {e}")
        with open('selcuk_sports_guncel_domain.txt', 'w', encoding='utf-8') as f:
            f.write("")

if __name__ == "__main__":
    main()
