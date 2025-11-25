#!/usr/bin/env python3
"""
01_precos_psic_saude_mental_prep.py

Unifica os preços de psicólogos/psiquiatras/psicoterapeutas de:
- Doctoralia
- BoaConsulta

E gera dois arquivos:
- dados_precos_unificados.csv       (nível profissional)
- precos_por_municipio.csv         (agregado por cidade/UF e tipo de profissional)
"""

import os
import unicodedata
import pandas as pd


# ---------- CONFIGURAÇÕES DE CAMINHO ----------

BASE_DOCTORALIA = "Doctoralia"
BASE_BOACONSULTA = "BoaConsulta"

PATH_DOC_PSICO = os.path.join(BASE_DOCTORALIA, "doctoralia_psicologos.csv")
PATH_DOC_PSIQ = os.path.join(BASE_DOCTORALIA, "doctoralia_psiquiatras.csv")

PATH_BC_PSICO = os.path.join(BASE_BOACONSULTA, "psicologos_boaconsulta.csv")
PATH_BC_PSIQ = os.path.join(BASE_BOACONSULTA, "psiquiatras_boaconsulta.csv")
PATH_BC_PSICOT = os.path.join(BASE_BOACONSULTA, "psicoterapeutas_boaconsulta.csv")

# Slugs que você usou nos scraps
CITY_SLUG_TO_NAME_UF = {
    "sao-paulo-sp": ("São Paulo", "SP"),
    "rio-de-janeiro-rj": ("Rio de Janeiro", "RJ"),
    "belo-horizonte-mg": ("Belo Horizonte", "MG"),
    "porto-alegre-rs": ("Porto Alegre", "RS"),
    "salvador-ba": ("Salvador", "BA"),
    # se tiver mais, coloca aqui
}


# ---------- FUNÇÕES AUXILIARES ----------


def normalize_str(s: str) -> str:
    """Remove acentos, deixa minúsculo e tira espaços extras para facilitar joins."""
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())


def load_doctoralia_psicologos(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # tira linhas de "xx opiniões"
    df = df[~df["nome"].astype(str).str.contains("opini", case=False, na=False)].copy()
    df["fonte"] = "doctoralia"
    df["tipo_profissional"] = "psicologo"
    return df


def load_doctoralia_psiquiatras(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[~df["nome"].astype(str).str.contains("opini", case=False, na=False)].copy()
    df["fonte"] = "doctoralia"
    df["tipo_profissional"] = "psiquiatra"
    return df


def load_boaconsulta_generic(path: str, tipo_profissional: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["fonte"] = "boaconsulta"
    df["tipo_profissional"] = tipo_profissional
    return df


def aplicar_municipio_oficial(df: pd.DataFrame) -> pd.DataFrame:
    """
    Usa o cidade_slug (quando existir) para definir cidade_oficial e uf_oficial
    de forma consistente entre Doctoralia e BoaConsulta.
    """
    df = df.copy()
    cidade_oficial = []
    uf_oficial = []

    for _, row in df.iterrows():
        slug = row.get("cidade_slug", None)
        c = row.get("cidade", None)
        uf = row.get("uf", None)

        if isinstance(slug, str) and slug in CITY_SLUG_TO_NAME_UF:
            nome, uf_slug = CITY_SLUG_TO_NAME_UF[slug]
            cidade_oficial.append(nome)
            uf_oficial.append(uf_slug)
        else:
            # fallback: usar o que vier da própria tabela
            cidade_oficial.append(c)
            uf_oficial.append(uf)

    df["cidade_oficial"] = cidade_oficial
    df["uf_oficial"] = uf_oficial
    df["cidade_norm"] = df["cidade_oficial"].apply(normalize_str)
    df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()

    return df


def preparar_precos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deixa apenas colunas relevantes e garante preço numérico.
    Espera colunas: nome, crp/crm, preco, cidade_oficial, uf_oficial, fonte, tipo_profissional
    """
    df = df.copy()

    # unificar coluna de registro (CRP/CRM) numa só
    if "crp" in df.columns and "crm" in df.columns:
        df["registro"] = df["crp"].fillna(df["crm"])
    elif "crp" in df.columns:
        df["registro"] = df["crp"]
    elif "crm" in df.columns:
        df["registro"] = df["crm"]
    else:
        df["registro"] = None

    # garantir preco numérico
    df["preco"] = pd.to_numeric(df["preco"], errors="coerce")

    # filtrar somente registros com preço
    df = df[df["preco"].notna()].copy()

    # selecionar colunas principais
    cols = [
        "nome",
        "registro",
        "tipo_profissional",
        "preco",
        "cidade_oficial",
        "uf_oficial",
        "fonte",
        "cidade_slug",
        "cidade_norm",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols]
    # tirar espaços extras no nome
    df["nome"] = df["nome"].astype(str).str.strip()

    # remover duplicados básicos (mesmo nome + cidade + uf + tipo + preço)
    df = df.drop_duplicates(
        subset=["nome", "cidade_oficial", "uf_oficial", "tipo_profissional", "preco"]
    )

    return df


def main():
    # ------ 1. Carrega bases de preços ------
    print("Carregando Doctoralia psicólogos...")
    doc_psico = load_doctoralia_psicologos(PATH_DOC_PSICO)

    print("Carregando Doctoralia psiquiatras...")
    doc_psiq = load_doctoralia_psiquiatras(PATH_DOC_PSIQ)

    print("Carregando BoaConsulta psicólogos...")
    bc_psico = load_boaconsulta_generic(PATH_BC_PSICO, "psicologo")

    print("Carregando BoaConsulta psiquiatras...")
    bc_psiq = load_boaconsulta_generic(PATH_BC_PSIQ, "psiquiatra")

    print("Carregando BoaConsulta psicoterapeutas...")
    bc_psicoter = load_boaconsulta_generic(PATH_BC_PSICOT, "psicoterapeuta")

    # ------ 2. Junta tudo ------
    df_all = pd.concat(
        [doc_psico, doc_psiq, bc_psico, bc_psiq, bc_psicoter],
        ignore_index=True,
    )

    # ------ 3. Define cidade_oficial e uf_oficial de forma consistente ------
    df_all = aplicar_municipio_oficial(df_all)

    # ------ 4. Limpa e padroniza preços ------
    df_prepared = preparar_precos(df_all)

    # ------ 5. Salva dados em nível profissional ------
    os.makedirs("output", exist_ok=True)
    out_prof = os.path.join("output", "dados_precos_unificados.csv")
    df_prepared.to_csv(out_prof, index=False, encoding="utf-8-sig")
    print(f"Salvo: {out_prof} (linhas: {len(df_prepared)})")

    # ------ 6. Agrega por município e tipo de profissional ------
    grp = (
        df_prepared.groupby(
            ["cidade_oficial", "uf_oficial", "cidade_norm", "tipo_profissional"],
            dropna=False,
        )["preco"]
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

    out_mun = os.path.join("output", "precos_por_municipio.csv")
    grp.to_csv(out_mun, index=False, encoding="utf-8-sig")
    print(f"Salvo: {out_mun} (linhas: {len(grp)})")


if __name__ == "__main__":
    main()
