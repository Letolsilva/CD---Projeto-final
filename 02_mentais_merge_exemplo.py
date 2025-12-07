#!/usr/bin/env python3
"""
02_mentais_merge_exemplo.py

Objetivo:
- Carregar MENTBR20–24 (t_mentais_datasus).
- Filtrar notificações de transtornos mentais F32 (depressão) e F41 (ansiedade).
- Agregar casos por município/ano.
- Vincular com:
    - preços médios de psicólogos/psiquiatras (precos_por_municipio.csv),
    - tabela de municípios (BR_Municipios_2023.csv),
    - CAPS_Municipios.csv (opcional).
- Gerar uma base integrada para análise (por ex.: ano 2023).

Pré-requisito:
- Rodar antes o script 01_precos_psic_saude_mental_prep.py
  para gerar output/precos_por_municipio.csv.
"""

import os
import unicodedata
import pandas as pd


BASE_MENTAIS = "t_mentais_datasus-main"

MENT_FILES = [
    "MENTBR20.csv",
    "MENTBR21.csv",
    "MENTBR22.csv",
    "MENTBR23.csv",
    "MENTBR24.csv",
]

PATH_PRECOS_MUN = os.path.join("output", "precos_por_municipio.csv")
PATH_MUNICIPIOS = os.path.join(BASE_MENTAIS, "BR_Municipios_2023.csv")
PATH_CAPS = os.path.join(BASE_MENTAIS, "CAPS_Municipios.csv")

COL_MUN_IBGE_MENT = "ID_MUNICIP"
COL_CID_MENT = "DIAG_ESP"
COL_ANO_MENT = "NU_ANO"

COL_MUN_IBGE_BR = "CD_MUN"
COL_NOME_MUN_BR = "NM_MUN"
COL_UF_BR = "SIGLA_UF"


def normalize_str(s: str) -> str:
    """Remove acentos, põe em minúsculo e tira espaços extras para facilitar joins."""
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())


def carregar_mentais() -> pd.DataFrame:
    """
    Lê MENTBR20–24, empilha e devolve um DataFrame único.
    Usa sep=None para deixar o pandas descobrir o separador (',' no seu caso).
    """
    dfs = []
    for fname in MENT_FILES:
        path = os.path.join(BASE_MENTAIS, fname)
        if not os.path.exists(path):
            print(f"⚠️ Arquivo não encontrado: {path} (pulando)")
            continue

        print(f"Lendo {path}...")
        df = pd.read_csv(path, sep=None, engine="python", encoding="latin1")

        if COL_ANO_MENT not in df.columns:
            sufixo = fname[-6:-4]
            ano_do_arquivo = int("20" + sufixo)
            df[COL_ANO_MENT] = ano_do_arquivo

        dfs.append(df)

    if not dfs:
        raise RuntimeError("Nenhum MENTBRxx foi carregado. Verifique caminhos/nomes.")

    ment = pd.concat(dfs, ignore_index=True)
    print("Colunas MENT unificado:", list(ment.columns))
    return ment


def filtrar_f32_f41(ment: pd.DataFrame) -> pd.DataFrame:
    """
    Mantém apenas registros com CID-10 começando em F32 (depressão) ou F41 (ansiedade).
    """
    df = ment.copy()

    if COL_CID_MENT not in df.columns:
        raise KeyError(
            f"Coluna {COL_CID_MENT!r} não encontrada no MENT. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    df[COL_CID_MENT] = df[COL_CID_MENT].astype(str).str.upper().str.strip()
    mask = df[COL_CID_MENT].str.startswith(("F32", "F41"), na=False)
    filtrado = df[mask].copy()
    print(f"Registros com F32/F41: {len(filtrado)} de {len(df)}")
    return filtrado


def agregar_mentais_por_municipio_ano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Conta o número de notificações F32/F41 por município/ano.
    Cada linha do MENT é um caso, então usamos .size().
    """
    df = df.copy()
    df[COL_MUN_IBGE_MENT] = df[COL_MUN_IBGE_MENT].astype(str).str.zfill(7)

    grp = (
        df.groupby([COL_MUN_IBGE_MENT, COL_ANO_MENT])
        .size()
        .reset_index(name="casos_f32_f41")
        .rename(columns={COL_MUN_IBGE_MENT: "cod_mun_ibge", COL_ANO_MENT: "ano"})
    )
    return grp


def carregar_municipios():
    """
    Carrega BR_Municipios_2023.csv do repositório t_mentais_datasus,
    deixando no padrão:

      CD_MUN     -> código IBGE do município (7 dígitos, string)
      NM_MUN     -> nome do município
      CD_UF      -> código numérico da UF (IBGE)
      SIGLA_UF   -> sigla da UF (SP, RJ, MG, ...)
      nome_norm  -> nome normalizado (sem acento, minúsculo) para merge
    """
    print("\n=== Carregando BR_Municipios_2023 ===")

    df = pd.read_csv(PATH_MUNICIPIOS, sep=None, engine="python")
    print("Colunas BR_Municipios_2023 (bruto):", list(df.columns))

    df = df.rename(
        columns={
            "codigo_ibge": "CD_MUN",
            "nome": "NM_MUN",
            "codigo_uf": "CD_UF",
        }
    )

    if "CD_MUN" not in df.columns:
        raise RuntimeError(
            "Não encontrei a coluna 'codigo_ibge' em BR_Municipios_2023.csv. "
            "Confere se o arquivo é o oficial do repositório t_mentais_datasus."
        )

    df["CD_MUN"] = df["CD_MUN"].astype(str).str.zfill(7)

    uf_map = {
        11: "RO",
        12: "AC",
        13: "AM",
        14: "RR",
        15: "PA",
        16: "AP",
        17: "TO",
        21: "MA",
        22: "PI",
        23: "CE",
        24: "RN",
        25: "PB",
        26: "PE",
        27: "AL",
        28: "SE",
        29: "BA",
        31: "MG",
        32: "ES",
        33: "RJ",
        35: "SP",
        41: "PR",
        42: "SC",
        43: "RS",
        50: "MS",
        51: "MT",
        52: "GO",
        53: "DF",
    }

    if "CD_UF" in df.columns:
        df["CD_UF"] = pd.to_numeric(df["CD_UF"], errors="coerce")
        df["SIGLA_UF"] = df["CD_UF"].map(uf_map)
    else:
        df["SIGLA_UF"] = ""

    df["nome_norm"] = df["NM_MUN"].apply(normalize_str)

    print("Colunas BR_Municipios_2023 (ajustado):", list(df.columns))
    return df


def carregar_caps() -> pd.DataFrame:
    """
    Carrega CAPS_Municipios.csv (opcional),
    renomeando IBGE -> CD_MUN e garantindo 7 dígitos.
    """
    if not os.path.exists(PATH_CAPS):
        print(f"⚠️ CAPS_Municipios.csv não encontrado em {PATH_CAPS} (ignorando CAPS).")
        return pd.DataFrame()

    df = pd.read_csv(PATH_CAPS, sep=None, engine="python", encoding="latin1")
    print("Colunas CAPS_Municipios (bruto):", list(df.columns))

    df = df.rename(
        columns={
            "IBGE": "CD_MUN",
            "Município": "NM_MUN",
            "Municipio": "NM_MUN",
        }
    )

    if "CD_MUN" in df.columns:
        df["CD_MUN"] = df["CD_MUN"].astype(str).str.zfill(7)
    else:
        print(
            "⚠️ Coluna IBGE não encontrada em CAPS_Municipios.csv, sem join por município."
        )
    return df


def carregar_precos_municipio() -> pd.DataFrame:
    """
    Carrega o arquivo gerado no script 01:
    output/precos_por_municipio.csv
    """
    df = pd.read_csv(PATH_PRECOS_MUN, encoding="utf-8-sig")
    print("Colunas precos_por_municipio:", list(df.columns))

    df["cidade_norm"] = df["cidade_norm"].apply(normalize_str)
    df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()
    return df


def anexar_ibge_a_precos(
    precos: pd.DataFrame, municipios: pd.DataFrame
) -> pd.DataFrame:
    """
    Faz join entre os preços médios por município e o código IBGE,
    usando (cidade_norm, UF) <-> (nome_norm, SIGLA_UF).
    """
    mun = municipios.copy()

    if "nome_norm" not in mun.columns:
        mun["nome_norm"] = mun[COL_NOME_MUN_BR].apply(normalize_str)

    mun[COL_UF_BR] = mun[COL_UF_BR].astype(str).str.upper().str.strip()

    merged = precos.merge(
        mun[[COL_MUN_IBGE_BR, "nome_norm", COL_UF_BR]],
        left_on=["cidade_norm", "uf_oficial"],
        right_on=["nome_norm", COL_UF_BR],
        how="left",
    )

    merged = merged.rename(columns={COL_MUN_IBGE_BR: "cod_mun_ibge"})
    merged["cod_mun_ibge"] = merged["cod_mun_ibge"].astype(str).str.zfill(7)
    return merged


def main():
    if not os.path.exists(PATH_PRECOS_MUN):
        raise FileNotFoundError(
            f"Arquivo {PATH_PRECOS_MUN} não encontrado. "
            "Rode antes o 01_precos_psic_saude_mental_prep.py."
        )
    precos = carregar_precos_municipio()

    if not os.path.exists(PATH_MUNICIPIOS):
        raise FileNotFoundError(f"Arquivo {PATH_MUNICIPIOS} não encontrado.")
    municipios = carregar_municipios()

    precos_ibge = anexar_ibge_a_precos(precos, municipios)
    print(
        "Linhas de precos com cod_mun_ibge preenchido:",
        precos_ibge["cod_mun_ibge"].notna().sum(),
    )

    caps = carregar_caps()

    ment = carregar_mentais()
    ment_filt = filtrar_f32_f41(ment)
    ment_agg = agregar_mentais_por_municipio_ano(ment_filt)

    ano_analise = 2023
    ment_ano = ment_agg[ment_agg["ano"] == ano_analise].copy()

    base = precos_ibge.merge(
        ment_ano,
        on="cod_mun_ibge",
        how="left",
    )

    if not caps.empty and "CD_MUN" in caps.columns:
        base = base.merge(
            caps[["CD_MUN", "Qtd_caps"]]
            if "Qtd_caps" in caps.columns
            else caps[["CD_MUN"]],
            left_on="cod_mun_ibge",
            right_on="CD_MUN",
            how="left",
            suffixes=("", "_caps"),
        )
        base = base.drop(columns=["CD_MUN"], errors="ignore")

    print("\nExemplo – psicólogos, preço médio vs. casos F32/F41 (primeiras linhas):")
    base_psico = base[base["tipo_profissional"] == "psicologo"].copy()
    print(
        base_psico[
            ["cidade_oficial", "uf_oficial", "preco_medio", "casos_f32_f41"]
        ].head(15)
    )

    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", f"base_precos_mentais_{ano_analise}.csv")
    base.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ Base integrada salva em: {out_path}")


if __name__ == "__main__":
    main()
