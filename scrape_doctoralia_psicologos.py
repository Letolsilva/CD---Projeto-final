#!/usr/bin/env python3
"""
Scraper simples para Doctoralia (lista de psicólogos por cidade).
- Salva CSV com: nome_anonimizado, cidade, bairro_endereco, servico, preco_raw, preco_num, perfil_url
- Use com responsabilidade e lentidão (sleep). Não abuse.
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import csv
import random
from urllib.parse import urljoin, urlparse
import pandas as pd
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DataScienceProject/1.0; +https://example.com/)",
    # coloque um contato real se for coletar muitos dados
}


def get_listing_page(city_slug, page=1):
    """
    Exemplo de URL: https://www.doctoralia.com.br/psicologo/sao-paulo
    Muitas listagens paginam com query params ou caminhos; aqui tentamos paginação via ?page=
    """
    base = f"https://www.doctoralia.com.br/psicologo/{city_slug}"
    if page and page != 1:
        url = f"{base}?page={page}"
    else:
        url = base
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text, url


def parse_price_text(text):
    """
    Extrai valor numérico do formato 'R$ 180' ou 'R$ 180' etc.
    Retorna (raw_text, float_value_or_None)
    """
    if not text:
        return "", None
    raw = text.strip()
    # pegar padrão como R$ 1.200,50 ou R$ 180
    m = re.search(r"R\$[\s\xa0]*([\d\.\,]+)", raw)
    if not m:
        return raw, None
    valtxt = m.group(1)
    # transformar 1.200,50 -> 1200.50
    val = valtxt.replace(".", "").replace(",", ".")
    try:
        return raw, float(val)
    except:
        return raw, None


def anonymize_name(name):
    """
    Simples anonimização: keep first name + initial of last name (if exists)
    """
    if not name:
        return ""
    parts = name.split()
    if len(parts) == 1:
        return parts[0]
    return parts[0] + " " + parts[-1][0] + "."


def parse_listing_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    # Observação: a estrutura do Doctoralia pode mudar. Aqui procuramos itens de lista.
    results = []
    # cada cartão de profissional costuma ter um elemento com atributo data-test ou classes específicas.
    # vamos procurar por blocos que contenham "Consulta Psicologia" ou "R$"
    # procura por containers de perfil — versátil:
    cards = soup.select("div.media, div.card, article")  # tentativa genérica
    # fallback: procurar links para perfis de psicólogos
    if not cards:
        cards = soup.find_all("a", href=True)

    # melhor estratégia: procurar por linhas que mostrem "Consulta Psicologia" ou "Preço" no texto
    # percorrer links de perfis (muitos sites tem <a href="/nome-sobrenome/psicologo/...
    for a in soup.select("a[href]"):
        href = a.get("href")
        # filtrar perfis que parecem ser de profissionais:
        if href and re.search(r"/[a-z0-9\-\_]+/psicologo", href):
            perfil_url = urljoin(base_url, href)
            # tentar extrair o bloco pai que contém preço e endereço
            parent = a.find_parent()
            block = parent
            # expandir procura por um nível ou dois
            for _ in range(3):
                # procurar preço no bloco atual
                text_block = block.get_text(separator="|", strip=True)
                if "R$" in text_block or "Consulta Psicologia" in text_block:
                    break
                if block.parent:
                    block = block.parent
            text = block.get_text(separator=" | ", strip=True)
            # tentar extrair nome do link de perfil (o texto do link)
            name = a.get_text(strip=True)
            # extrair preço a partir do text
            # pegar a primeira ocorrência de "R$ ...", ou "Consultar valores" -> None
            price_match = re.search(r"R\$[\s\xa0]*[\d\.\,]+", text)
            price_text = price_match.group(0) if price_match else ""
            price_raw, price_num = parse_price_text(price_text)
            # tentar extrair local (bairro/cidade) — na listagem muitas vezes aparece perto de '•' ou 'Mapa'
            bairro = ""
            # heurística: partes separadas por "•" (bullet) ou "|"
            parts = [p.strip() for p in re.split(r"•|\|", text) if p.strip()]
            # procurar por algo que pareça endereço (tem números ou 'Rua' ou 'Av.' ou cidade)
            for p in parts:
                if re.search(r"\d", p) or any(
                    k in p.lower()
                    for k in [
                        "rua",
                        "av.",
                        "avenida",
                        "bairro",
                        "mapa",
                        "são",
                        "rio",
                        "bh",
                        "salvador",
                        "fortaleza",
                        "brasil",
                    ]
                ):
                    bairro = p
                    break
            # tentar extrair o serviço descrito (ex: "Consulta Psicologia")
            service = ""
            mserv = re.search(
                r"(Consulta|Primeira consulta|Retorno).{0,30}",
                text,
                flags=re.IGNORECASE,
            )
            if mserv:
                service = mserv.group(0)
            results.append(
                {
                    "nome": name,
                    "nome_anon": anonymize_name(name),
                    "perfil_url": perfil_url,
                    "texto_bloco": text,
                    "bairro_endereco": bairro,
                    "servico": service,
                    "preco_raw": price_raw,
                    "preco_num": price_num,
                }
            )
    # Deduplicar por perfil_url
    uniq = {}
    for r in results:
        uniq[r["perfil_url"]] = r
    return list(uniq.values())


def scrape_city(city_slug, max_pages=3, delay_range=(1.0, 2.5)):
    all_items = []
    for page in range(1, max_pages + 1):
        print(f"Buscando {city_slug} — página {page}")
        try:
            html, url = get_listing_page(city_slug, page)
        except Exception as e:
            print("Erro ao baixar página:", e)
            break
        items = parse_listing_html(html, url)
        print(f"Encontrados ~{len(items)} itens na página {page}")
        all_items.extend(items)
        # delay respeitando robots.txt (crawl-delay)
        time.sleep(random.uniform(*delay_range))
    # transformar em DataFrame e retornar
    df = pd.DataFrame(all_items)
    return df


def main():
    # Exemplo: cidades (slugs) que você quer raspar
    cidades = {
        "sao-paulo": "São Paulo",
        "rio-de-janeiro": "Rio de Janeiro",
        "belo-horizonte": "Belo Horizonte",
    }
    all_dfs = []
    for slug, nome_cidade in cidades.items():
        df = scrape_city(slug, max_pages=2)  # cuidado: comece com poucas páginas
        if not df.empty:
            df["cidade"] = nome_cidade
            all_dfs.append(df)
    if all_dfs:
        result = pd.concat(all_dfs, ignore_index=True)
    else:
        result = pd.DataFrame()

    # limpar e salvar
    if not result.empty:
        # remover duplicatas por perfil_url + serviço + preco
        result = result.drop_duplicates(subset=["perfil_url", "servico", "preco_raw"])
        # reordenar colunas
        cols = [
            "nome_anon",
            "cidade",
            "bairro_endereco",
            "servico",
            "preco_raw",
            "preco_num",
            "perfil_url",
            "texto_bloco",
        ]
        for c in cols:
            if c not in result.columns:
                result[c] = ""
        result = result[cols]
        result.to_csv(
            "doctoralia_psicologos_precos.csv", index=False, encoding="utf-8-sig"
        )
        print("Salvo em doctoralia_psicologos_precos.csv — linhas:", len(result))
    else:
        print("Nenhum dado coletado.")


if __name__ == "__main__":
    main()
