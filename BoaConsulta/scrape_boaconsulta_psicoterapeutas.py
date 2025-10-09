# scrape_boa_consulta_psicoterapeutas.py

import re
import time
import os
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

USE_SELENIUM = False

BASE = "https://www.boaconsulta.com"
CITY_SLUGS = [
    "sao-paulo-sp",
    "rio-de-janeiro-rj",
    "belo-horizonte-mg",
    "porto-alegre-rs",
    "salvador-ba",
]
OUTPUT_FILE = "psicoterapeutas_boaconsulta.csv"
CACHE_DIR = "cache_profiles_psicoterapeutas"
MAX_PAGES_PER_CITY = 80
MAX_WORKERS = 6

os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": BASE + "/",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

if USE_SELENIUM:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        print("⚠️ Selenium não disponível:", e)
        USE_SELENIUM = False


def parse_price(text):
    if not text:
        return None
    m = re.search(r"R\$\s*([\d\.\,]+)", text)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except:
        return None


def get_list_url_for_city(city_slug, page=None):
    # Especialidade “psicoterapeutas”
    base = f"{BASE}/especialistas/psicoterapeutas/{city_slug}/particular?s=2"
    if page and page > 1:
        return f"{base}&page={page}"
    return base


def get_profile_id(profile_url):
    m = re.search(r"/especialista/([^/?]+)", profile_url)
    return m.group(1) if m else None


def get_profile_from_cache(profile_id):
    path = os.path.join(CACHE_DIR, f"{profile_id}.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def save_profile_to_cache(profile_id, html):
    path = os.path.join(CACHE_DIR, f"{profile_id}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def fetch_page_requests(url):
    try:
        r = session.get(url, timeout=25)
    except Exception as e:
        print(f"❌ Erro de conexão para {url}: {e}")
        raise

    if r.status_code != 200:
        print(f"⚠️ Status {r.status_code} para {url}")
        snippet = (r.text or "")[:800].replace("\n", " ")
        print(">>> Trecho da resposta (início):")
        print(snippet)
        r.raise_for_status()

    return r.text


def fetch_page_selenium(url):
    options = Options()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    try:
        driver.get(url)
        time.sleep(1.0)
        html = driver.page_source
    finally:
        driver.quit()
    return html


def fetch_page(url):
    if USE_SELENIUM:
        try:
            html = fetch_page_selenium(url)
        except Exception as e:
            print("⚠️ Selenium falhou:", e)
            html = fetch_page_requests(url)
    else:
        html = fetch_page_requests(url)

    lower = (html or "").lower()
    if (
        ("captcha" in lower)
        or ("attention required" in lower)
        or ("checking your browser" in lower)
    ):
        print("⚠️ Possível proteção anti-bot na URL:", url)
        snippet = html[:800].replace("\n", " ")
        print(">>> Trecho da resposta (início):")
        print(snippet)

    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def extract_crp_and_price_city(profile_url):
    """
    Extrai: CRP (ou equivalente), preço, cidade do perfil de psicoterapeuta.
    Retorna (crp, price, city)
    Se não conseguir extrair, retorna None nos campos correspondentes.
    """
    profile_id = get_profile_id(profile_url)
    if not profile_id:
        return None, None, None

    # cache
    html = get_profile_from_cache(profile_id)
    if html is None:
        try:
            soup_tmp = fetch_page(profile_url)
            html = soup_tmp.prettify()
            save_profile_to_cache(profile_id, html)
            time.sleep(0.3)
        except Exception as e:
            print("❌ Falha ao baixar perfil:", profile_url, e)
            return None, None, None

    # parse
    soup = BeautifulSoup(html, "lxml")

    # CRP ou registro — psicoterapeuta pode ter CRP ou talvez apenas registro de psicologia
    crp = None
    el_reg = soup.select_one("p.text-xs")
    if el_reg:
        text = el_reg.get_text(strip=True)
        if text.startswith("CRP") or text.startswith("CRM"):
            crp = text

    # Preço — similar aos outros casos
    price = None
    for li in soup.select("div.mt-10 li.font-bold h3"):
        txt = li.get_text()
        if "Preço da consulta" in txt:
            span = li.find("span")
            if span:
                price = parse_price(span.get_text())
            break

    # Cidade do perfil
    city = None
    city_el = soup.select_one("h3.speakable-locations-name")
    if city_el:
        city = city_el.get_text(strip=True)

    return crp, price, city


def parse_cards(soup, city_slug, writer, seen):
    cards = soup.select("div[itemtype='http://schema.org/Physician']")
    profiles = []

    for card in cards:
        name_el = card.select_one("h3 a span[itemprop='name']")
        name = name_el.get_text(strip=True) if name_el else None

        link_el = card.select_one("h3 a")
        profile_url = urljoin(BASE, link_el["href"].split("?")[0]) if link_el else None

        uf_el = card.select_one("span[itemprop='addressRegion']")
        uf = uf_el.get_text(strip=True) if uf_el else None

        if name and profile_url and (name, profile_url) not in seen:
            seen.add((name, profile_url))
            profiles.append((name, profile_url, uf, city_slug))

    if not profiles:
        return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_prof = {
            executor.submit(extract_crp_and_price_city, p[1]): p for p in profiles
        }
        for future in as_completed(future_to_prof):
            name, url, uf, city_slug = future_to_prof[future]
            try:
                crp, price, city = future.result()
            except Exception as e:
                print("❌ Erro ao processar perfil:", url, e)
                crp, price, city = None, None, None

            if not price:
                continue

            row = {
                "nome": name,
                "preco": price,
                "cidade": city,
                "uf": uf,
                "crp": crp,
                "url": url,
                "cidade_slug": city_slug,
            }
            writer.writerow(row)
            print("✔️", row)


def scrape_city(city_slug, writer, seen):
    for page in range(1, MAX_PAGES_PER_CITY + 1):
        url = get_list_url_for_city(city_slug, page=page)
        print("⤴️ Acessando:", url)
        try:
            soup = fetch_page(url)
        except Exception as e:
            print("⚠️ Falha ao acessar página (continuando):", url, e)
            time.sleep(2.0)
            continue

        before = len(seen)
        parse_cards(soup, city_slug, writer, seen)

        if len(seen) == before:
            print("🔚 Sem novos registros nesta cidade/página, pulando.")
            break

        time.sleep(1.0)


def load_seen_from_csv():
    seen = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seen.add((row.get("nome"), row.get("url")))
    return seen


def main():
    file_exists = os.path.isfile(OUTPUT_FILE)
    seen = load_seen_from_csv()

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["nome", "preco", "cidade", "uf", "crp", "url", "cidade_slug"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for slug in CITY_SLUGS:
            print(f"\n📍 Coletando psicoterapeutas em {slug}...")
            scrape_city(slug, writer, seen)

    print("\n✅ Finalizado! Dados gravados em", OUTPUT_FILE)


if __name__ == "__main__":
    main()
