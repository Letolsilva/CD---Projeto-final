#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import time
import re
import random
from urllib.parse import urljoin, urlencode
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DataScienceProject/1.0; +https://example.com/)",
}

CITY_SLUGS = [
    "sao-paulo-sp",
    "rio-de-janeiro-rj",
    "belo-horizonte-mg",
    "porto-alegre-rs",
    "salvador-ba",
]

# Mapeia slug -> cidade bonitinha / UF / texto do "loc" da busca
CITY_INFO = {
    "sao-paulo-sp": {
        "cidade": "São Paulo",
        "uf": "SP",
        "loc": "São Paulo",
    },
    "rio-de-janeiro-rj": {
        "cidade": "Rio de Janeiro",
        "uf": "RJ",
        "loc": "Rio de Janeiro",
    },
    "belo-horizonte-mg": {
        "cidade": "Belo Horizonte",
        "uf": "MG",
        "loc": "Belo Horizonte",
    },
    "porto-alegre-rs": {
        "cidade": "Porto Alegre",
        "uf": "RS",
        "loc": "Porto Alegre",
    },
    "salvador-ba": {
        "cidade": "Salvador",
        "uf": "BA",
        "loc": "Salvador",
    },
}

BASE_SEARCH_URL = "https://www.doctoralia.com.br/pesquisa"

# Especialidades:
SPECIALIZATIONS = {
    "psicologo": {
        "q": "Psicólogo",
        "spec_id": 76,
    },
    "psiquiatra": {
        "q": "Psiquiatra",
        "spec_id": 78,
    },
}

# Controles básicos
MAX_PAGES = 100  # máximo de páginas por cidade/especialidade
DELAY_RANGE = (1.0, 2.0)  # segundos entre requisições


def parse_price_text(text):
    """
    Extrai valor numérico de 'R$ 180', 'a partir de r$ 300', etc.
    Retorna (raw_text, float_value_or_None)
    """
    if not text:
        return "", None
    raw = text.strip()
    m = re.search(r"[Rr]\$[\s\xa0]*([\d\.\,]+)", raw)
    if not m:
        return raw, None
    valtxt = m.group(1)
    val = valtxt.replace(".", "").replace(",", ".")
    try:
        return raw, float(val)
    except Exception:
        return raw, None


def get_search_page(query, loc, spec_id, page=1):
    """
    Monta e baixa a página de pesquisa.
    Exemplo base:
    https://www.doctoralia.com.br/pesquisa?q=Psiquiatra&loc=São+Paulo&filters[specializations][]=78&page=2
    """
    params = {
        "q": query,
        "loc": loc,
        "filters[specializations][]": spec_id,
    }
    if page > 1:
        params["page"] = page

    url = f"{BASE_SEARCH_URL}?{urlencode(params, doseq=True)}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text, url


def parse_listing_html(html, base_url, tipo, loc_cidade):
    """
    Lê o HTML da página de pesquisa e extrai:
    nome, url, preço, bairro/região, CRM/CRP/CFP etc.
    tipo: "psicologo" ou "psiquiatra"
    loc_cidade: ex. "São Paulo" (serve pra filtrar resultados de outras cidades)
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Regex pra identificar URL de perfil
    if tipo == "psicologo":
        prof_pattern = r"/[a-z0-9\-\_]+/psicolog"
    else:
        prof_pattern = r"/[a-z0-9\-\_]+/psiquiatra"

    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue

        # filtrar perfis
        if not re.search(prof_pattern, href, flags=re.IGNORECASE):
            continue

        perfil_url = urljoin(base_url, href)

        # subir alguns níveis pra pegar o "cartão" inteiro
        block = a
        for _ in range(5):
            if not block.parent:
                break
            block = block.parent
            text_block = block.get_text(separator=" | ", strip=True)
            if any(
                key in text_block.lower()
                for key in ["crp", "crm", "cfp", "consulta", "primeira consulta", "r$"]
            ):
                break

        text = block.get_text(separator=" | ", strip=True)

        # filtrar só resultados da cidade de interesse (loc_cidade)
        if loc_cidade.lower() not in text.lower():
            # pode ser teleconsulta sem cidade explícita; se quiser manter, comente esse 'continue'
            pass  # aqui optei por não excluir, pra não perder teleconsulta

        name = a.get_text(strip=True)
        if not name:
            continue

        # preço: primeira ocorrência de R$
        price_match = re.search(r"[Rr]\$[\s\xa0]*[\d\.\,]+", text)
        price_text = price_match.group(0) if price_match else ""
        price_raw, price_num = parse_price_text(price_text)

        # se não tiver preço, ignorar (seu pedido)
        if price_num is None:
            continue

        # CRM / CRP / CFP etc — pega um trechinho que contenha isso
        crp_crm = ""
        m_cr = re.search(
            r"(CRP[^|]*|CRM[^|]*|CFP[^|]*|CRO[^|]*|CRE[^|]*)",
            text,
            flags=re.IGNORECASE,
        )
        if m_cr:
            crp_crm = m_cr.group(0).strip()

        # tentar extrair região/bairro — linha com Rua/Av./Avenida ou que seja só o bairro
        regiao = ""
        parts = [p.strip() for p in text.split(" | ") if p.strip()]
        for p in parts:
            low = p.lower()
            if any(k in low for k in ["rua ", "av.", "avenida", "rodovia", "travessa"]):
                regiao = p
                break
        # segunda tentativa: bairros típicos (sem 'rua')
        if not regiao:
            for p in parts:
                if any(
                    k in p.lower()
                    for k in [
                        "bairro",
                        "são paulo",
                        "rio de janeiro",
                        "belo horizonte",
                        "porto alegre",
                        "salvador",
                    ]
                ):
                    regiao = p
                    break

        results.append(
            {
                "nome": name,
                "preco": price_num,
                "preco_raw": price_raw,
                "crp": crp_crm,
                "url": perfil_url,
                "regiao": regiao,
            }
        )

    # deduplicar por url (mantendo o último registro)
    uniq = {}
    for r in results:
        uniq[r["url"]] = r
    return list(uniq.values())


def scrape_professional_type(tipo):
    """
    tipo: "psicologo" ou "psiquiatra"
    Retorna DataFrame com colunas:
    nome, preco, cidade, uf, crp, url, cidade_slug, regiao, preco_raw
    """
    spec_info = SPECIALIZATIONS[tipo]
    all_rows = []

    for cidade_slug in CITY_SLUGS:
        info = CITY_INFO[cidade_slug]
        cidade = info["cidade"]
        uf = info["uf"]
        loc = info["loc"]

        print(f"== {tipo.upper()} :: {cidade_slug} ({cidade}/{uf}) ==")

        seen_urls = set()

        for page in range(1, MAX_PAGES + 1):
            try:
                html, url = get_search_page(
                    query=spec_info["q"],
                    loc=loc,
                    spec_id=spec_info["spec_id"],
                    page=page,
                )
            except Exception as e:
                print(f"Erro ao baixar página {page} de {cidade_slug} ({tipo}): {e}")
                break

            rows = parse_listing_html(html, url, tipo=tipo, loc_cidade=cidade)
            # tirar os já vistos
            new_rows = [r for r in rows if r["url"] not in seen_urls]

            print(
                f"  {cidade_slug} página {page}: {len(rows)} registros, {len(new_rows)} novos"
            )

            if not new_rows:
                # se não veio nada novo, provavelmente acabou a paginação
                if page > 1:
                    break

            for r in new_rows:
                r["cidade"] = cidade
                r["uf"] = uf
                r["cidade_slug"] = cidade_slug
                seen_urls.add(r["url"])
                all_rows.append(r)

            time.sleep(random.uniform(*DELAY_RANGE))

    if not all_rows:
        return pd.DataFrame(
            columns=[
                "nome",
                "preco",
                "cidade",
                "uf",
                "crp",
                "url",
                "cidade_slug",
                "regiao",
                "preco_raw",
            ]
        )

    df = pd.DataFrame(all_rows)

    # garantir colunas
    for col in [
        "nome",
        "preco",
        "cidade",
        "uf",
        "crp",
        "url",
        "cidade_slug",
        "regiao",
        "preco_raw",
    ]:
        if col not in df.columns:
            df[col] = ""

    # filtrar só quem realmente tem preço numérico
    df = df[df["preco"].notna()]

    # remover duplicatas por url + preco
    df = df.drop_duplicates(subset=["url", "preco"])

    # reordenar
    df = df[
        [
            "nome",
            "preco",
            "cidade",
            "uf",
            "crp",
            "url",
            "cidade_slug",
            "regiao",
            "preco_raw",
        ]
    ]

    return df


def main():
    # Psicólogos
    df_psic = scrape_professional_type("psicologo")
    if not df_psic.empty:
        df_psic.to_csv(
            "doctoralia_psicologos.csv",
            index=False,
            encoding="utf-8-sig",
        )
        print("Salvo doctoralia_psicologos.csv:", len(df_psic), "linhas")
    else:
        print("Nenhum psicólogo com preço encontrado.")

    # Psiquiatras
    df_psiq = scrape_professional_type("psiquiatra")
    if not df_psiq.empty:
        df_psiq.to_csv(
            "doctoralia_psiquiatras.csv",
            index=False,
            encoding="utf-8-sig",
        )
        print("Salvo doctoralia_psiquiatras.csv:", len(df_psiq), "linhas")
    else:
        print("Nenhum psiquiatra com preço encontrado.")


if __name__ == "__main__":
    main()
