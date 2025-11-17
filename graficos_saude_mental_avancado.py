#!/usr/bin/env python3
"""
Gera gráficos avançados cruzando:
- Preços de psicólogos / psicoterapeutas / psiquiatras (Doctoralia + BoaConsulta)
- CAPS por UF
- Notificações de transtornos mentais relacionados ao trabalho (MENTBR20–24, Datasus)

Gráficos gerados:
1) Barplot: preço mediano por tipo (psicólogo / psiquiatra / psicoterapeuta) por UF
2) Barplot: proporção de psiquiatras na oferta privada por UF
3) Scatter: notificações por 100 CAPS vs proporção de psiquiatras
4) Scatter: notificações por 100 profissionais vs preço mediano de psiquiatras
5) Série temporal 2020–2024 de notificações para UFs presentes na base de preços
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re

# ============================
# 1. Configuração de caminhos
# ============================

BASE_DIR = Path(".").resolve()

DOCTORALIA_PSICO = BASE_DIR / "Doctoralia/doctoralia_psicologos.csv"
DOCTORALIA_PSIQ = BASE_DIR / "Doctoralia/doctoralia_psiquiatras.csv"
BOACONSULTA_PSICO = BASE_DIR / "BoaConsulta/psicologos_boaconsulta.csv"
BOACONSULTA_PSIQ = BASE_DIR / "BoaConsulta/psiquiatras_boaconsulta.csv"
BOACONSULTA_PSICOTER = BASE_DIR / "BoaConsulta/psicoterapeutas_boaconsulta.csv"
DATASUS_DIR = BASE_DIR / "t_mentais_datasus-main"

UF_REGEX = re.compile(r"\b([A-Z]{2})\b")

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


# ============================
# 2. Funções auxiliares
# ============================


def infer_uf_from_row(row, crp_col="crp", uf_col="uf"):
    """
    Tenta inferir UF:
    1) Se a coluna 'uf' já tem sigla de 2 letras, usa.
    2) Caso contrário, procura sigla de UF no campo CRP.
    Ex: "CRM 129050 SP" -> "SP"
    """
    uf = row.get(uf_col)
    if isinstance(uf, str) and len(uf) == 2 and uf.isalpha():
        return uf.upper()

    crp = row.get(crp_col)
    if isinstance(crp, str):
        tokens = crp.replace("-", " ").split()
        for token in reversed(tokens):
            if len(token) == 2 and token.isalpha():
                return token.upper()
        m = UF_REGEX.search(crp)
        if m:
            return m.group(1).upper()

    return None


# ============================
# 3. Carregar profissionais e preços
# ============================


def load_profissionais():
    # Carregar CSVs
    doc_psico = pd.read_csv(DOCTORALIA_PSICO, encoding="utf-8-sig")
    doc_psiq = pd.read_csv(DOCTORALIA_PSIQ, encoding="utf-8-sig")
    boa_psico = pd.read_csv(BOACONSULTA_PSICO, encoding="utf-8-sig")
    boa_psiq = pd.read_csv(BOACONSULTA_PSIQ, encoding="utf-8-sig")
    boa_psicoter = pd.read_csv(BOACONSULTA_PSICOTER, encoding="utf-8-sig")

    # UF final (Doctoralia já tem uf na coluna 'uf')
    doc_psico["uf_final"] = doc_psico["uf"].astype(str).str.upper()
    doc_psiq["uf_final"] = doc_psiq["uf"].astype(str).str.upper()

    # BoaConsulta: inferir UF a partir do CRP
    for df in [boa_psico, boa_psiq, boa_psicoter]:
        df["uf_final"] = df.apply(infer_uf_from_row, axis=1)

    # Tag tipo de profissional
    doc_psico["tipo"] = "psicologo"
    boa_psico["tipo"] = "psicologo"

    boa_psicoter["tipo"] = "psicoterapeuta"

    doc_psiq["tipo"] = "psiquiatra"
    boa_psiq["tipo"] = "psiquiatra"

    # Fonte
    frames = []
    for name, df in [
        ("doctoralia_psicologos", doc_psico),
        ("doctoralia_psiquiatras", doc_psiq),
        ("psicologos_boaconsulta", boa_psico),
        ("psiquiatras_boaconsulta", boa_psiq),
        ("psicoterapeutas_boaconsulta", boa_psicoter),
    ]:
        tmp = df.copy()
        tmp["fonte"] = name
        frames.append(tmp)

    prof_all = pd.concat(frames, ignore_index=True)

    # Filtros: ter preço e UF
    prof_all = prof_all[pd.notna(prof_all["preco"])]
    prof_all = prof_all[pd.notna(prof_all["uf_final"])]

    # Normalizar UF
    prof_all["UF"] = prof_all["uf_final"].astype(str).str.upper()

    return prof_all


# ============================
# 4. CAPS e notificações Datasus
# ============================


def load_caps_by_uf():
    caps_path = DATASUS_DIR / "CAPS_Municipios.csv"
    caps = pd.read_csv(caps_path, encoding="utf-8-sig")
    caps_by_uf = (
        caps.groupby("UF", as_index=False)["Qtd_caps"]
        .sum()
        .rename(columns={"Qtd_caps": "caps_total"})
    )
    return caps_by_uf


def load_notificacoes_uf():
    """
    Lê MENTBR20–24 e devolve:
        UF (sigla) | notificacoes_2020_2024
    """
    ment_files = sorted(DATASUS_DIR.glob("MENTBR*.csv"))
    dfs = []

    for path in ment_files:
        df = pd.read_csv(path, encoding="utf-8-sig")

        if "SG_UF" in df.columns:
            df["UF_ibge"] = df["SG_UF"].astype(str).str.zfill(2)
        elif "SG_UF_NOT" in df.columns:
            df["UF_ibge"] = df["SG_UF_NOT"].astype(str).str.zfill(2)
        else:
            continue

        df["UF"] = df["UF_ibge"].map(IBGE_TO_UF)
        dfs.append(df[["UF"]])

    ment_all = pd.concat(dfs, ignore_index=True)
    ment_summary = (
        ment_all.groupby("UF", as_index=False)
        .size()
        .rename(columns={"size": "notificacoes_2020_2024"})
    )
    return ment_summary


def load_notificacoes_trend(target_ufs):
    """
    Série temporal 2020–2024 de notificações para UFs de interesse.
    """
    ment_files = sorted(DATASUS_DIR.glob("MENTBR*.csv"))
    dfs = []

    for path in ment_files:
        year_digits = [int(s) for s in re.findall(r"\d{2}", path.name)]
        year = 2000 + year_digits[0]

        df = pd.read_csv(path, encoding="utf-8-sig")

        if "SG_UF" in df.columns:
            df["UF_ibge"] = df["SG_UF"].astype(str).str.zfill(2)
        elif "SG_UF_NOT" in df.columns:
            df["UF_ibge"] = df["SG_UF_NOT"].astype(str).str.zfill(2)
        else:
            continue

        df["UF"] = df["UF_ibge"].map(IBGE_TO_UF)
        df["ANO"] = year
        dfs.append(df[["UF", "ANO"]])

    ment_trend = pd.concat(dfs, ignore_index=True)

    trend_summary = (
        ment_trend[ment_trend["UF"].isin(target_ufs)]
        .groupby(["UF", "ANO"])
        .size()
        .reset_index(name="notificacoes")
    )

    return trend_summary


# ============================
# 5. Montar tabela UF estendida
# ============================


def build_uf_extended(prof_all):
    # Debug: verificar dados disponíveis
    print("Tipos de profissionais únicos:", prof_all["tipo"].unique())
    print("UFs únicas:", prof_all["UF"].unique())
    print("Total de registros:", len(prof_all))

    # Counts e medianas por UF/tipo
    pivot_counts = prof_all.pivot_table(
        index="UF", columns="tipo", values="nome", aggfunc="count", fill_value=0
    )
    pivot_med = prof_all.pivot_table(
        index="UF", columns="tipo", values="preco", aggfunc="median"
    )

    print("Colunas do pivot_counts:", pivot_counts.columns.tolist())
    print("Pivot counts shape:", pivot_counts.shape)

    # CAPS e notificações
    caps_by_uf = load_caps_by_uf()
    ment_summary = load_notificacoes_uf()

    uf_table = pivot_counts.reset_index()
    uf_table = uf_table.merge(caps_by_uf, on="UF", how="left").merge(
        ment_summary, on="UF", how="left"
    )

    # Totais e proporções - usar fillna para colunas que podem não existir
    psicologo_col = uf_table["psicologo"] if "psicologo" in uf_table.columns else 0
    psicoter_col = (
        uf_table["psicoterapeuta"] if "psicoterapeuta" in uf_table.columns else 0
    )
    psiquiatra_col = uf_table["psiquiatra"] if "psiquiatra" in uf_table.columns else 0

    uf_table["total_privados"] = psicologo_col + psicoter_col + psiquiatra_col

    # Evitar divisão por zero
    uf_table["proporcao_psiquiatras"] = 0
    mask = uf_table["total_privados"] > 0
    if "psiquiatra" in uf_table.columns:
        uf_table.loc[mask, "proporcao_psiquiatras"] = (
            uf_table.loc[mask, "psiquiatra"] / uf_table.loc[mask, "total_privados"]
        )

    uf_table["notificacoes_por_100_caps"] = (
        uf_table["notificacoes_2020_2024"] / uf_table["caps_total"] * 100
    )

    uf_table["notificacoes_por_100_privados"] = (
        uf_table["notificacoes_2020_2024"] / uf_table["total_privados"] * 100
    )

    # Relação de preços psiquiatra/psicólogo
    price_ratio = pivot_med.copy()
    price_ratio["psiq_psico_ratio"] = price_ratio.get("psiquiatra") / price_ratio.get(
        "psicologo"
    )

    # Rename columns to avoid conflicts in merge
    price_cols = price_ratio[
        ["psicologo", "psiquiatra", "psiq_psico_ratio"]
    ].reset_index()
    price_cols = price_cols.rename(
        columns={"psicologo": "preco_psicologo", "psiquiatra": "preco_psiquiatra"}
    )

    uf_extended = uf_table.merge(
        price_cols,
        on="UF",
        how="left",
    )

    return uf_extended, pivot_med


# ============================
# 6. Gráficos
# ============================


def graf_preco_mediano_por_tipo_uf(pivot_med):
    """
    Barplot de mediana de preço por tipo de profissional em cada UF.
    """
    plt.figure(figsize=(12, 6))
    pivot_med.sort_index().plot(kind="bar", width=0.8)
    plt.title("Preço mediano por tipo de profissional e UF")
    plt.xlabel("UF")
    plt.ylabel("Preço mediano (R$)")
    plt.xticks(rotation=45)
    plt.legend(title="Tipo de profissional")
    plt.tight_layout()
    plt.savefig("graf_preco_mediano_tipo_uf.png", dpi=200)
    plt.show()


def graf_proporcao_psiquiatras(uf_extended):
    """
    Barplot: proporção de psiquiatras na oferta privada, por UF.
    """
    data = uf_extended.sort_values("proporcao_psiquiatras", ascending=False)

    plt.figure(figsize=(8, 5))
    plt.bar(data["UF"], data["proporcao_psiquiatras"])
    plt.title("Proporção de psiquiatras entre profissionais privados, por UF")
    plt.xlabel("UF")
    plt.ylabel("Proporção de psiquiatras")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("graf_proporcao_psiquiatras_por_uf.png", dpi=200)
    plt.show()


def graf_notif_por_caps_vs_proporcao_psiq(uf_extended):
    """
    Scatter: notificações por 100 CAPS vs proporção de psiquiatras.
    """
    data = uf_extended.dropna(
        subset=["notificacoes_por_100_caps", "proporcao_psiquiatras"]
    )

    plt.figure(figsize=(8, 6))
    plt.scatter(data["notificacoes_por_100_caps"], data["proporcao_psiquiatras"])

    for _, row in data.iterrows():
        plt.text(
            row["notificacoes_por_100_caps"],
            row["proporcao_psiquiatras"],
            row["UF"],
            fontsize=8,
            ha="center",
            va="bottom",
        )

    plt.title("Notificações/100 CAPS vs proporção de psiquiatras (por UF)")
    plt.xlabel("Notificações de transtornos mentais por 100 CAPS (2020–2024)")
    plt.ylabel("Proporção de psiquiatras na oferta privada")
    plt.tight_layout()
    plt.savefig("graf_notif_por_caps_vs_proporcao_psiq.png", dpi=200)
    plt.show()


def graf_notif_por_privado_vs_preco_psiq(uf_extended):
    """
    Scatter: notificações por 100 profissionais vs preço mediano de psiquiatras.
    """
    data = uf_extended.dropna(
        subset=["notificacoes_por_100_privados", "preco_psiquiatra"]
    )

    plt.figure(figsize=(8, 6))
    plt.scatter(data["notificacoes_por_100_privados"], data["preco_psiquiatra"])

    for _, row in data.iterrows():
        plt.text(
            row["notificacoes_por_100_privados"],
            row["preco_psiquiatra"],
            row["UF"],
            fontsize=8,
            ha="center",
            va="bottom",
        )

    plt.title("Notificações/100 profissionais vs preço mediano de psiquiatras")
    plt.xlabel("Notificações de transtornos mentais por 100 profissionais (2020–2024)")
    plt.ylabel("Preço mediano de psiquiatras (R$)")
    plt.tight_layout()
    plt.savefig("graf_notif_por_privado_vs_preco_psiq.png", dpi=200)
    plt.show()


def graf_trend_notificacoes(trend_summary):
    """
    Série temporal de notificações 2020–2024 para as UFs presentes na base de preços.
    """
    pivot = trend_summary.pivot(index="ANO", columns="UF", values="notificacoes")

    plt.figure(figsize=(10, 6))
    for uf in pivot.columns:
        plt.plot(pivot.index, pivot[uf], marker="o", label=uf)

    plt.title(
        "Notificações de transtornos mentais relacionados ao trabalho (2020–2024)"
    )
    plt.xlabel("Ano")
    plt.ylabel("Número de notificações")
    plt.legend(title="UF")
    plt.tight_layout()
    plt.savefig("graf_trend_notificacoes_2020_2024.png", dpi=200)
    plt.show()


# ============================
# 7. Main
# ============================


def main():
    print("Carregando profissionais...")
    prof_all = load_profissionais()

    print("Montando tabela estendida por UF...")
    uf_extended, pivot_med = build_uf_extended(prof_all)

    print("\nColunas disponíveis em uf_extended:")
    print(uf_extended.columns.tolist())
    print("\nPrimeiras linhas de uf_extended:")
    print(uf_extended.head())

    print("\nUFs com dados:")
    # Usar .get() para evitar KeyError se as colunas não existirem
    available_cols = ["UF", "caps_total", "notificacoes_2020_2024", "total_privados"]
    if "psicologo" in uf_extended.columns:
        available_cols.append("psicologo")
    if "psiquiatra" in uf_extended.columns:
        available_cols.append("psiquiatra")
    if "preco_psicologo" in uf_extended.columns:
        available_cols.append("preco_psicologo")
    if "preco_psiquiatra" in uf_extended.columns:
        available_cols.append("preco_psiquiatra")

    print(uf_extended[available_cols].round(2))  # Gráficos de preço e composição
    graf_preco_mediano_por_tipo_uf(pivot_med)
    graf_proporcao_psiquiatras(uf_extended)
    graf_notif_por_caps_vs_proporcao_psiq(uf_extended)
    graf_notif_por_privado_vs_preco_psiq(uf_extended)

    # Série temporal só para UFs que aparecem na base de preço
    ufs_interesse = uf_extended["UF"].dropna().unique().tolist()
    trend_summary = load_notificacoes_trend(ufs_interesse)
    graf_trend_notificacoes(trend_summary)

    # Salvar tabela UF estendida para análise em Excel/PowerBI se quiser
    uf_extended.round(3).to_csv(
        "uf_extended_profissionais_caps_notificacoes.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print("\nTabela detalhada salva em uf_extended_profissionais_caps_notificacoes.csv")


if __name__ == "__main__":
    main()
