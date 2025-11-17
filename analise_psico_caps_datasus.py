#!/usr/bin/env python3
"""
Integra preços de consultas psicológicas (Doctoralia / BoaConsulta)
com dados de CAPS e notificações de transtornos mentais do trabalho (DATASUS).

Saída principal: um DataFrame por UF com:
- n_profissionais
- preco_medio, preco_mediano
- caps_total
- notificacoes_transtornos_mentais_2020_2024
- notificacoes_por_caps
- notificacoes_por_prof
- caps_por_prof

Opcional: salva em summary_precos_caps_transtornos_por_UF.csv
"""

import pandas as pd
import re
from pathlib import Path

# ==========================
# 1. CONFIGURAÇÕES DE CAMINHO
# ==========================

BASE_DIR = Path(".").resolve()

# Arquivos de preço (na mesma pasta do script, ajuste se necessário)
DOCTORALIA_PSICO_PATH = BASE_DIR / "Doctoralia/doctoralia_psicologos.csv"
BOACONSULTA_PSICO_PATH = BASE_DIR / "BoaConsulta/psicologos_boaconsulta.csv"
BOACONSULTA_PSICOTER_PATH = BASE_DIR / "BoaConsulta/psicoterapeutas_boaconsulta.csv"

# Pasta do repositório t_mentais_datasus (clonado ou extraído do zip)
DATASUS_DIR = BASE_DIR / "t_mentais_datasus-main"

# ==========================
# 2. MAPAS E FUNÇÕES AUXILIARES
# ==========================

# Mapa IBGE UF -> sigla UF
IBGE_TO_UF = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}

UF_REGEX = re.compile(r"\b([A-Z]{2})\b")


def infer_uf_from_row(row) -> str | None:
    """
    Tenta inferir UF:
    1) Se coluna 'uf' já tem algo tipo 'SP', usa.
    2) Senão, procura sigla no texto do CRP (ex: 'CRP 06/49654-7 SP').
    """
    uf = row.get("uf")
    if isinstance(uf, str) and len(uf) == 2 and uf.isalpha():
        return uf.upper()

    crp = row.get("crp")
    if isinstance(crp, str):
        # Tenta pegar a última "palavra" de 2 letras
        tokens = crp.replace("-", " ").split()
        for token in reversed(tokens):
            if len(token) == 2 and token.isalpha():
                return token.upper()
        # fallback: regex qualquer sigla de UF
        m = UF_REGEX.search(crp)
        if m:
            return m.group(1).upper()

    return None


# ==========================
# 3. CARREGAR E RESUMIR PREÇOS POR UF
# ==========================


def load_psico_price_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carrega:
      - doctoralia_psicologos.csv
      - psicologos_boaconsulta.csv
      - psicoterapeutas_boaconsulta.csv

    Infere UF, junta tudo num único DataFrame de profissionais
    e devolve também o resumo por UF (price_by_uf).
    """
    # Carregar
    doctoralia_psicologos = pd.read_csv(DOCTORALIA_PSICO_PATH, encoding="utf-8-sig")
    psicologos_boaconsulta = pd.read_csv(BOACONSULTA_PSICO_PATH, encoding="utf-8-sig")
    psicoterapeutas_boaconsulta = pd.read_csv(
        BOACONSULTA_PSICOTER_PATH, encoding="utf-8-sig"
    )

    # Inferir UF final
    for df in [psicologos_boaconsulta, psicoterapeutas_boaconsulta]:
        df["uf_final"] = df.apply(infer_uf_from_row, axis=1)

    doctoralia_psicologos["uf_final"] = (
        doctoralia_psicologos["uf"].astype(str).str.upper()
    )

    # Adicionar coluna de origem
    frames = []
    for name, df in [
        ("doctoralia_psicologos", doctoralia_psicologos),
        ("psicologos_boaconsulta", psicologos_boaconsulta),
        ("psicoterapeutas_boaconsulta", psicoterapeutas_boaconsulta),
    ]:
        tmp = df.copy()
        tmp["fonte"] = name
        frames.append(tmp)

    psico_all = pd.concat(frames, ignore_index=True)

    # Filtros: ter preço e UF conhecida
    psico_all = psico_all[pd.notna(psico_all["preco"])]
    psico_all = psico_all[pd.notna(psico_all["uf_final"])]

    # Resumo por UF
    price_by_uf = (
        psico_all.groupby("uf_final")
        .agg(
            n_profissionais=("nome", "count"),
            preco_medio=("preco", "mean"),
            preco_mediano=("preco", "median"),
            preco_p25=("preco", lambda x: x.quantile(0.25)),
            preco_p75=("preco", lambda x: x.quantile(0.75)),
        )
        .reset_index()
        .rename(columns={"uf_final": "UF"})
    )

    # Arredondar preços para ficar mais bonitinho
    for col in ["preco_medio", "preco_mediano", "preco_p25", "preco_p75"]:
        price_by_uf[col] = price_by_uf[col].round(2)

    return psico_all, price_by_uf


# ==========================
# 4. CARREGAR CAPS E NOTIFICAÇÕES (DATASUS)
# ==========================


def load_caps_by_uf() -> pd.DataFrame:
    """
    Lê CAPS_Municipios.csv e devolve DataFrame com:
        UF, caps_total
    """
    caps_path = DATASUS_DIR / "CAPS_Municipios.csv"
    caps = pd.read_csv(caps_path, encoding="utf-8-sig")
    caps_by_uf = (
        caps.groupby("UF", as_index=False)["Qtd_caps"]
        .sum()
        .rename(columns={"Qtd_caps": "caps_total"})
    )
    return caps_by_uf


def load_notificacoes_transtornos_mentais() -> pd.DataFrame:
    """
    Lê MENTBR20–MENTBR24 e devolve DataFrame com:
        UF (sigla), notificacoes_transtornos_mentais_2020_2024

    Obs: Os arquivos usam códigos IBGE de UF (11, 35, etc.),
    então fazemos o mapeamento para siglas (RO, SP, etc.).
    """
    ment_files = sorted([p for p in DATASUS_DIR.glob("MENTBR*.csv")])

    dfs = []
    for path in ment_files:
        df = pd.read_csv(path, encoding="utf-8-sig")

        # algumas versões usam SG_UF, outras SG_UF_NOT
        if "SG_UF" in df.columns:
            df["UF_ibge"] = df["SG_UF"].astype(str).str.zfill(2)
        elif "SG_UF_NOT" in df.columns:
            df["UF_ibge"] = df["SG_UF_NOT"].astype(str).str.zfill(2)
        else:
            continue

        # Ano (se quiser usar depois)
        if "NU_ANO" in df.columns:
            df["ANO"] = df["NU_ANO"]
        # Se não, poderia derivar do nome do arquivo, mas não é necessário agora

        dfs.append(df[["UF_ibge"]])

    ment_all = pd.concat(dfs, ignore_index=True)

    # Mapeia código IBGE -> sigla
    ment_all["UF"] = ment_all["UF_ibge"].map(IBGE_TO_UF)

    ment_summary = (
        ment_all.groupby("UF", as_index=False)
        .size()
        .rename(columns={"size": "notificacoes_transtornos_mentais_2020_2024"})
    )

    return ment_summary


# ==========================
# 5. INTEGRAR TUDO E CRIAR INDICADORES
# ==========================


def build_summary():
    """
    Integra:
      - preços por UF
      - CAPS por UF
      - notificações de transtornos mentais por UF

    E cria indicadores derivados.
    """
    # Preços
    psico_all, price_by_uf = load_psico_price_data()

    # CAPS
    caps_by_uf = load_caps_by_uf()

    # Notificações
    ment_summary = load_notificacoes_transtornos_mentais()

    # Garantir tipo string nas chaves UF
    price_by_uf["UF"] = price_by_uf["UF"].astype(str)
    caps_by_uf["UF"] = caps_by_uf["UF"].astype(str)
    ment_summary["UF"] = ment_summary["UF"].astype(str)

    # Join: preços + CAPS + notificações
    summary = price_by_uf.merge(caps_by_uf, on="UF", how="left").merge(
        ment_summary, on="UF", how="left"
    )

    # Indicadores derivados
    summary["notificacoes_por_caps"] = (
        summary["notificacoes_transtornos_mentais_2020_2024"] / summary["caps_total"]
    )

    summary["notificacoes_por_prof"] = (
        summary["notificacoes_transtornos_mentais_2020_2024"]
        / summary["n_profissionais"]
    )

    summary["caps_por_prof"] = summary["caps_total"] / summary["n_profissionais"]

    # Arredondar indicadores
    for col in ["notificacoes_por_caps", "notificacoes_por_prof", "caps_por_prof"]:
        summary[col] = summary[col].round(3)

    return psico_all, summary


# ==========================
# 6. MAIN
# ==========================


def main():
    psico_all, summary = build_summary()

    print("\n=== Resumo por UF (ordenado por preço mediano) ===\n")
    print(
        summary.sort_values("preco_mediano", ascending=False)[
            [
                "UF",
                "n_profissionais",
                "preco_medio",
                "preco_mediano",
                "caps_total",
                "notificacoes_transtornos_mentais_2020_2024",
                "notificacoes_por_caps",
                "notificacoes_por_prof",
                "caps_por_prof",
            ]
        ]
    )

    # Opcional: salvar para CSV
    out_path = BASE_DIR / "summary_precos_caps_transtornos_por_UF.csv"
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nArquivo salvo em: {out_path}")


if __name__ == "__main__":
    main()
