#!/usr/bin/env python3
"""
06_treemap_precos_mentais_static.py

Treemap estática dos dados de saúde mental por REGIÃO e UF.

- Cada bloco grande = região do Brasil
- Cada retângulo dentro = UF
- Tamanho do retângulo = PREÇO MÉDIO PONDERADO da UF
  (ponderado pela quantidade de profissionais)
- Cor do retângulo = região

Gera APENAS uma imagem PNG (sem hover) em:
  output/treemap_precos_mentais.png
"""

import os
import pandas as pd
import plotly.express as px


BASE_PATH = os.path.join("output", "base_precos_mentais_2020_2024.csv")
if not os.path.exists(BASE_PATH):
    raise FileNotFoundError(f"Arquivo {BASE_PATH} não encontrado.")

df = pd.read_csv(BASE_PATH, encoding="utf-8-sig")

# ====================================================================
# REGIÕES DO BRASIL
# ====================================================================
uf_to_regiao = {
    # Norte
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    # Nordeste
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    # Centro-Oeste
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    # Sudeste
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    # Sul
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()
df["regiao"] = df["uf_oficial"].map(uf_to_regiao).fillna("Outros")

# Se não tiver coluna de CAPS, cria com zero pra não quebrar (mesmo que não usemos)
if "Qtd_caps" not in df.columns:
    df["Qtd_caps"] = 0

# ====================================================================
# AGREGAÇÕES POR UF
# ====================================================================

# Preços médios por UF e tipo (psicólogo / psiquiatra)
agg_tp = df.groupby(["uf_oficial", "tipo_profissional"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    qtd_profissionais=("qtd_profissionais", "sum"),
)

# Pivotar preços para ter uma coluna por tipo
precos = (
    agg_tp.pivot(index="uf_oficial", columns="tipo_profissional", values="preco_medio")
    .rename(
        columns={
            "psicologo": "preco_psicologo",
            "psiquiatra": "preco_psiquiatra",
        }
    )
    .reset_index()
)

# Qtd total de profissionais por UF
qtd_total = (
    agg_tp.groupby("uf_oficial", as_index=False)["qtd_profissionais"]
    .sum()
    .rename(columns={"qtd_profissionais": "qtd_profissionais_total"})
)

# Preço médio ponderado da UF (pelos profissionais de cada tipo)
ponderado = (
    agg_tp.assign(prod=lambda d: d["preco_medio"] * d["qtd_profissionais"])
    .groupby("uf_oficial", as_index=False)
    .agg(
        soma_prod=("prod", "sum"),
        qtd_total=("qtd_profissionais", "sum"),
    )
)
ponderado["preco_medio_uf"] = ponderado["soma_prod"] / ponderado["qtd_total"]
ponderado = ponderado[["uf_oficial", "preco_medio_uf"]]

# Montar DF final da treemap (não vamos usar hover, então info extra é opcional)
treemap_df = (
    precos.merge(qtd_total, on="uf_oficial", how="left")
    .merge(ponderado, on="uf_oficial", how="left")
    .merge(df[["uf_oficial", "regiao"]].drop_duplicates(), on="uf_oficial", how="left")
)

# ====================================================================
# TREEMAP ESTÁTICA
# ====================================================================

color_map = {
    "Norte": "#64b5f6",
    "Nordeste": "#ffb74d",
    "Centro-Oeste": "#81c784",
    "Sudeste": "#ba68c8",
    "Sul": "#4db6ac",
    "Outros": "#b0bec5",
}

fig = px.treemap(
    treemap_df,
    path=["regiao", "uf_oficial"],  # nível 1: região, nível 2: UF
    values="preco_medio_uf",  # área = preço médio ponderado
    color="regiao",
    color_discrete_map=color_map,
    width=900,
    height=500,
)

# Bordas, cores e texto
fig.update_traces(
    marker=dict(line=dict(width=1, color="white")),
    textinfo="label",
    root_color="whitesmoke",
    hoverinfo="skip",  # desativa hover (não importa na imagem, mas fica explícito)
)

fig.update_layout(
    title={
        "text": "Preço médio de saúde mental por região e UF",
        "x": 0.5,
        "xanchor": "center",
    },
    margin=dict(t=70, l=10, r=10, b=10),
    uniformtext_minsize=9,
    uniformtext_mode="hide",
)

# ====================================================================
# SALVAR APENAS A IMAGEM (PNG)
# ====================================================================
os.makedirs("output", exist_ok=True)
out_path = os.path.join("output", "treemap_precos_mentais.png")

# requer 'kaleido' instalado: pip install -U kaleido
fig.write_image(out_path, scale=2)  # scale>1 pra ficar mais nítido

print(f"✅ Treemap estática salva em: {out_path}")
