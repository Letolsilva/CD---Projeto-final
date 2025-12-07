#!/usr/bin/env python3

import os
import pandas as pd
import plotly.express as px

BASE_PATH = os.path.join("output", "base_precos_mentais_2020_2024.csv")
if not os.path.exists(BASE_PATH):
    raise FileNotFoundError(f"Arquivo {BASE_PATH} não encontrado.")

df = pd.read_csv(BASE_PATH, encoding="utf-8-sig")

uf_to_regiao = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()
df["regiao"] = df["uf_oficial"].map(uf_to_regiao).fillna("Outros")

if "Qtd_caps" not in df.columns:
    df["Qtd_caps"] = 0

agg_tp = df.groupby(["uf_oficial", "tipo_profissional"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    qtd_profissionais=("qtd_profissionais", "sum"),
)

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

qtd_total = (
    agg_tp.groupby("uf_oficial", as_index=False)["qtd_profissionais"]
    .sum()
    .rename(columns={"qtd_profissionais": "qtd_profissionais_total"})
)

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

treemap_df = (
    precos.merge(qtd_total, on="uf_oficial", how="left")
    .merge(ponderado, on="uf_oficial", how="left")
    .merge(df[["uf_oficial", "regiao"]].drop_duplicates(), on="uf_oficial", how="left")
)

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
    path=["regiao", "uf_oficial"],
    values="preco_medio_uf",
    color="regiao",
    color_discrete_map=color_map,
    width=900,
    height=500,
)

fig.update_traces(
    marker=dict(line=dict(width=1, color="white")),
    textinfo="label",
    root_color="whitesmoke",
    hoverinfo="skip",
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

os.makedirs("output", exist_ok=True)
out_path = os.path.join("output", "treemap_precos_mentais.png")

fig.write_image(out_path, scale=2)

print(f"✅ Treemap estática salva em: {out_path}")
