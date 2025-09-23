import re
import time
import math
import csv
import json
import random
import string
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.boaconsulta.com"
# Ex.: cidade "São Paulo - SP" → slug "sao-paulo-sp"
CITY_SLUGS = [
    "sao-paulo-sp",
    "rio-de-janeiro-rj",
    "belo-horizonte-mg",
    "porto-alegre-rs",
    "salvador-ba",
    # adicione outras cidades aqui
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0; +https://example.org/bot)"
}

# Alguns resultados mostram 10 itens por página; a paginação costuma aceitar ?page=2
# Vamos tentar até não encontrar novos cards ou atingir um limite de segurança.
MAX_PAGES_PER_CITY = 80  # limite de segurança
REQUEST_DELAY_SEC = (1.2, 2.4)  # intervalo aleatório entre requisições

CARD_SELECTOR = "div:has(h3) + p, div:has(h3)"  # fallback para capturar blocos; ajustaremos com buscas mais específicas


def parse_price(text):
    # Pega "R$ 200,00" como 200.00
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


def extract_city_state_from_address(addr):
    # Endereço termina com "- Cidade - UF"
    # Ex.: "... - Vila Mariana, São Paulo - SP"
    city, uf = None, None
    # Tenta padrões com vírgula antes do traço
    m = re.search(r",\s*([^,-]+?)\s*-\s*([A-Z]{2})\s*$", addr)
    if not m:
        # Plano B: último "- Cidade - UF"
        m = re.search(r"-\s*([^,-]+?)\s*-\s*([A-Z]{2})\s*$", addr)
    if m:
        city = m.group(1).strip()
        uf = m.group(2).strip()
    return city, uf


def extract_neighborhood_from_address(addr):
    # Pega o trecho do bairro antes de ", Cidade - UF" ou "- Cidade - UF"
    # Ex.: "Rua ... - Tatuapé, São Paulo - SP" → "Tatuapé"
    # Ex.: "Avenida Paulista, 807 - Jardim Paulista, São Paulo - SP" → "Jardim Paulista"
    if not addr:
        return None
    # Primeiro, remova o sufixo ", Cidade - UF" para isolar o bairro
    addr_clean = re.sub(r",\s*[^,-]+?\s*-\s*[A-Z]{2}\s*$", "", addr)
    # O bairro normalmente vem após o último " - "
    parts = [p.strip() for p in addr_clean.split(" - ")]
    if len(parts) >= 2:
        return parts[-1]  # última parte costuma ser o bairro
    return None


def get_list_url_for_city(city_slug, page=None):
    base = f"{BASE}/especialistas/psicologia-geral/{city_slug}"
    if page and page > 1:
        return f"{base}?page={page}"
    return base


def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def parse_cards(soup):
    items = []
    cards = soup.select("div[itemtype='http://schema.org/Physician']")
    for card in cards:
        # Nome
        name_el = card.select_one("h3 a span[itemprop='name']")
        name = name_el.get_text(strip=True) if name_el else None

        # Endereço (texto)
        addr_el = None
        for p in card.select("p.font-bold"):
            if "Endereço" in p.get_text():
                addr_el = p.find_next_sibling("p")
                break
        addr = addr_el.get_text(" ", strip=True) if addr_el else None

        # Cidade e UF direto dos metadados
        city_el = card.select_one("span[itemprop='addressLocality']")
        uf_el = card.select_one("span[itemprop='addressRegion']")
        city = (
            city_el["content"].strip()
            if city_el and city_el.has_attr("content")
            else (city_el.get_text(strip=True) if city_el else None)
        )
        uf = (
            uf_el["content"].strip()
            if uf_el and uf_el.has_attr("content")
            else (uf_el.get_text(strip=True) if uf_el else None)
        )

        # Bairro (último pedaço do endereço antes da cidade)
        bairro = None
        if addr and city and uf:
            bairro = addr.replace(f"{city} - {uf}", "").strip()
            if " - " in bairro:
                bairro = bairro.split(" - ")[-1].strip()

        # Valor
        price = None
        for p in card.select("p.font-bold"):
            if "Valor" in p.get_text():
                price_el = p.find_next_sibling("div")
                if price_el:
                    price = parse_price(price_el.get_text())
                break

        if name:
            items.append(
                {
                    "nome": name,
                    "preco": price,
                    "endereco": addr,
                    "bairro": bairro,
                    "cidade": city,
                    "uf": uf,
                }
            )
    return items


def scrape_city(city_slug):
    all_rows = []
    seen = set()
    for page in range(1, MAX_PAGES_PER_CITY + 1):
        url = get_list_url_for_city(city_slug, page=page)
        try:
            soup = fetch_page(url)
        except Exception as e:
            # Falha na página → parar essa cidade
            break

        rows = parse_cards(soup)
        # Evita loops infinitos se a paginação não funcionar
        new_rows = []
        for r in rows:
            key = (r["nome"], r.get("endereco"))
            if key not in seen:
                seen.add(key)
                new_rows.append(r)

        if not new_rows:
            # Sem novos cards → encerra
            break

        all_rows.extend(new_rows)

        # Heurística: se a página trouxe muito poucos itens, pode ser a última
        if len(new_rows) < 5:
            # provavelmente acabou
            pass

        time.sleep(random.uniform(*REQUEST_DELAY_SEC))
    # Anotar a cidade/UF a partir do slug se faltou no endereço
    if all_rows:
        city_human = city_slug.replace("-", " ").title()
        for r in all_rows:
            if not r["cidade"]:
                r["cidade"] = city_human.rsplit(" ", 1)[0]
            if not r["uf"] and len(city_slug.split("-")) >= 2:
                r["uf"] = city_slug.split("-")[-1].upper()
    return all_rows


def main():
    all_data = []
    for slug in CITY_SLUGS:
        print(f"Coletando {slug}...")
        rows = scrape_city(slug)
        for r in rows:
            r["cidade_slug"] = slug
        all_data.extend(rows)

    df = pd.DataFrame(all_data).drop_duplicates()

    # CSV detalhado (por profissional)
    df.to_csv(
        "psicologos_boaconsulta_profissionais.csv", index=False, encoding="utf-8-sig"
    )

    # Agregação por região
    # “Região” aqui = cidade (e, se quiser, também bairro dentro da cidade)
    agg_city = (
        df.groupby(["cidade", "uf"], dropna=False)["preco"]
        .agg(["count", "mean", "median", "min", "max"])
        .reset_index()
        .rename(
            columns={
                "count": "qtd_profissionais",
                "mean": "preco_medio",
                "median": "preco_mediano",
                "min": "preco_min",
                "max": "preco_max",
            }
        )
    )

    agg_bairro = (
        df.groupby(["cidade", "uf", "bairro"], dropna=False)["preco"]
        .agg(["count", "mean", "median", "min", "max"])
        .reset_index()
        .rename(
            columns={
                "count": "qtd_profissionais",
                "mean": "preco_medio",
                "median": "preco_mediano",
                "min": "preco_min",
                "max": "preco_max",
            }
        )
        .sort_values(
            ["cidade", "uf", "qtd_profissionais"], ascending=[True, True, False]
        )
    )

    # Exporta ambas as visões num só CSV (abaixo, bairro; você pode salvar também em arquivo separado)
    agg_bairro.to_csv(
        "psicologos_boaconsulta_por_regiao.csv", index=False, encoding="utf-8-sig"
    )

    print("OK!")
    print("Arquivos gerados:")
    print(" - psicologos_boaconsulta_profissionais.csv")
    print(" - psicologos_boaconsulta_por_regiao.csv")


if __name__ == "__main__":
    main()
