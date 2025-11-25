#!/usr/bin/env python3
"""
02_mentais_merge_multi_anos.py

Objetivo:
- Carregar MENTBR20–24 (t_mentais_datasus-main).
- Filtrar notificações de transtornos mentais F32 (depressão) e F41 (ansiedade).
- Agregar casos por município/ano.
- Vincular com:
    - preços médios de psicólogos/psiquiatras (precos_por_municipio.csv),
    - tabela de municípios (BR_Municipios_2023.csv),
    - CAPS_Municipios.csv (Qtd_caps por município).
- Gerar base integrada multianual: 2020–2024.

Pré-requisito:
- Rodar antes o script 01_precos_psic_saude_mental_prep.py
  para gerar output/precos_por_municipio.csv.
"""

import os
import unicodedata
import pandas as pd

# ----------------------------------------------------------------------
# CONFIGURAÇÕES DE CAMINHO
# ----------------------------------------------------------------------

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

# ----------------------------------------------------------------------
# COLUNAS
# ----------------------------------------------------------------------

COL_MUN_IBGE_MENT = "ID_MUNICIP"  # MENTBRxx
COL_CID_MENT = "DIAG_ESP"
COL_ANO_MENT = "NU_ANO"

COL_MUN_IBGE_BR = "CD_MUN"
COL_NOME_MUN_BR = "NM_MUN"
COL_UF_BR = "SIGLA_UF"

# ----------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ----------------------------------------------------------------------


def normalize_str(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())


def carregar_mentais() -> pd.DataFrame:
    """
    Lê MENTBR20–24, empilha e devolve um DataFrame único.
    """
    dfs = []
    for fname in MENT_FILES:
        path = os.path.join(BASE_MENTAIS, fname)
        if not os.path.exists(path):
            print(f"⚠️ Arquivo não encontrado: {path} (pulando)")
            continue

        print(f"Lendo {path}...")
        # IMPORTANTE: MENTBRxx está em CSV com vírgula e aspas, não com ';'
        df = pd.read_csv(
            path,
            sep=",",  # separador correto
            encoding="latin1",  # encoding
        )

        # garante que a coluna de ano exista (deve ser NU_ANO, mas só por segurança)
        if COL_ANO_MENT not in df.columns:
            sufixo = fname[-6:-4]  # "20", "21" ...
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
    df = df.copy()
    df[COL_MUN_IBGE_MENT] = df[COL_MUN_IBGE_MENT].astype(str).str.zfill(7)

    grp = (
        df.groupby([COL_MUN_IBGE_MENT, COL_ANO_MENT])
        .size()
        .reset_index(name="casos_f32_f41")
        .rename(columns={COL_MUN_IBGE_MENT: "cod_mun_ibge", COL_ANO_MENT: "ano"})
    )
    return grp


def carregar_municipios() -> pd.DataFrame:
    """
    Carrega BR_Municipios_2023.csv do repositório t_mentais_datasus-main,
    detectando corretamente o separador (é CSV com vírgula).
    Ajusta colunas para: CD_MUN, NM_MUN, SIGLA_UF, nome_norm.
    """
    print("\n=== Carregando BR_Municipios_2023 ===")

    # 1ª tentativa: ler com separador padrão (vírgula)
    df = pd.read_csv(PATH_MUNICIPIOS, encoding="utf-8")
    # Se vier tudo grudado em uma coluna, tentamos de novo com sep=","
    if len(df.columns) == 1:
        df = pd.read_csv(PATH_MUNICIPIOS, sep=",", encoding="utf-8")

    print("Colunas BR_Municipios_2023 (bruto):", list(df.columns))

    # Renomear para um padrão comum
    df = df.rename(
        columns={
            "codigo_ibge": "CD_MUN",
            "nome": "NM_MUN",
            "codigo_uf": "CD_UF",
        }
    )

    # Garantir que CD_MUN existe
    if "CD_MUN" not in df.columns:
        raise ValueError(
            "Não encontrei a coluna 'codigo_ibge' em BR_Municipios_2023.csv. "
            "Confira o cabeçalho do arquivo."
        )

    # Código IBGE com 7 dígitos
    df["CD_MUN"] = df["CD_MUN"].astype(str).str.zfill(7)

    # Mapear UF numérica -> sigla
    UF_MAP = {
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
        df["SIGLA_UF"] = df["CD_UF"].map(UF_MAP)
    else:
        # fallback: se por algum motivo não tiver CD_UF
        df["SIGLA_UF"] = None

    # Normalizar nome para facilitar join por string
    df["nome_norm"] = (
        df["NM_MUN"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )

    print("Colunas BR_Municipios_2023 (ajustado):", list(df.columns))
    return df


def carregar_caps() -> pd.DataFrame:
    """
    Carrega CAPS_Municipios.csv.
    O arquivo do repositório t_mentais_datasus vem separado por vírgula,
    com cabeçalho algo como: UF,IBGE,Município,Qtd_caps
    """
    if not os.path.exists(PATH_CAPS):
        print(f"⚠️ CAPS_Municipios.csv não encontrado em {PATH_CAPS} (ignorando CAPS).")
        return pd.DataFrame()

    print("\n=== Carregando CAPS_Municipios ===")

    # tenta ler como CSV padrão (vírgula)
    df = pd.read_csv(PATH_CAPS, encoding="latin1")

    # se por algum motivo vier tudo em uma coluna só, tenta "explodir" manualmente
    if len(df.columns) == 1:
        colname = df.columns[0]
        print("⚠️ CAPS veio em uma coluna só, tentando separar por vírgula...")
        tmp = df[colname].str.split(",", expand=True)
        # força o nome das colunas
        tmp.columns = ["UF", "IBGE", "Municipio", "Qtd_caps"]
        df = tmp

    # limpa espacinhos nos nomes das colunas
    df.columns = [c.strip() for c in df.columns]
    print("Colunas CAPS_Municipios (ajustado):", list(df.columns))

    if "IBGE" not in df.columns or "Qtd_caps" not in df.columns:
        raise ValueError(
            "Não encontrei as colunas 'IBGE' e 'Qtd_caps' em CAPS_Municipios.csv. "
            "Confira o cabeçalho do arquivo."
        )

    # padronizar código IBGE com 7 dígitos
    df["IBGE"] = df["IBGE"].astype(str).str.zfill(7)

    # garantir Qtd_caps numérico
    df["Qtd_caps"] = (
        pd.to_numeric(df["Qtd_caps"], errors="coerce").fillna(0).astype(int)
    )

    return df


def carregar_precos_municipio() -> pd.DataFrame:
    df = pd.read_csv(PATH_PRECOS_MUN, encoding="utf-8-sig")
    print("Colunas precos_por_municipio:", list(df.columns))

    df["cidade_norm"] = df["cidade_norm"].apply(normalize_str)
    df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()
    return df


def anexar_ibge_a_precos(
    precos: pd.DataFrame, municipios: pd.DataFrame
) -> pd.DataFrame:
    mun = municipios.copy()
    mun["nome_norm"] = mun["nome_norm"].apply(normalize_str)

    merged = precos.merge(
        mun[[COL_MUN_IBGE_BR, "nome_norm", COL_UF_BR]],
        left_on=["cidade_norm", "uf_oficial"],
        right_on=["nome_norm", COL_UF_BR],
        how="left",
    )

    merged = merged.rename(columns={COL_MUN_IBGE_BR: "cod_mun_ibge"})
    merged["cod_mun_ibge"] = merged["cod_mun_ibge"].astype(str).str.zfill(7)
    return merged


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------


def main():
    # 1) Preços por município
    if not os.path.exists(PATH_PRECOS_MUN):
        raise FileNotFoundError(
            f"Arquivo {PATH_PRECOS_MUN} não encontrado. "
            "Rode antes o 01_precos_psic_saude_mental_prep.py."
        )
    precos = carregar_precos_municipio()

    # 2) Municípios IBGE
    if not os.path.exists(PATH_MUNICIPIOS):
        raise FileNotFoundError(f"Arquivo {PATH_MUNICIPIOS} não encontrado.")
    municipios = carregar_municipios()

    # 3) Vincular IBGE
    precos_ibge = anexar_ibge_a_precos(precos, municipios)
    print(
        "Linhas de precos com cod_mun_ibge preenchido:",
        precos_ibge["cod_mun_ibge"].notna().sum(),
    )

    # 4) CAPS
    caps = carregar_caps()

    # 5) MENTBR20–24
    ment = carregar_mentais()
    ment_filt = filtrar_f32_f41(ment)
    ment_agg = agregar_mentais_por_municipio_ano(ment_filt)

    # 6) Join multi-anos (não filtramos ano aqui)
    base = precos_ibge.merge(
        ment_agg,
        on="cod_mun_ibge",
        how="left",
    )

    # 7) Anexar CAPS (Qtd_caps) se existir
    if not caps.empty:
        base = base.merge(
            caps,
            left_on="cod_mun_ibge",
            right_on="IBGE",
            how="left",
        )
        base = base.drop(columns=["IBGE"], errors="ignore")

    # 8) Salvar
    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", "base_precos_mentais_2020_2024.csv")
    base.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ Base integrada multianual salva em: {out_path}")


if __name__ == "__main__":
    main()
