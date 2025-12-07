#!/usr/bin/env python3

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from unidecode import unidecode

PATH_PRECOS = "output/precos_por_municipio.csv"
PATH_MUN = "t_mentais_datasus-main/BR_Municipios_2023.csv"

mun = pd.read_csv(PATH_MUN, encoding="utf-8")
mun["codigo_ibge"] = mun["codigo_ibge"].astype(str).str.zfill(7)
mun["nome_norm"] = mun["nome"].apply(lambda x: unidecode(str(x)).lower())
mun["uf"] = (
    mun["codigo_ibge"]
    .str[:2]
    .map(
        {
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
            "32": "ES",
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
    )
)

precos = pd.read_csv(PATH_PRECOS, encoding="utf-8")
precos["cidade_norm"] = precos["cidade_norm"].apply(lambda x: unidecode(str(x)).lower())

df_merged = precos.merge(mun, left_on="cidade_norm", right_on="nome_norm", how="left")
df_merged = df_merged.dropna(subset=["latitude", "longitude", "preco_medio"])

df_uf = df_merged.groupby(["uf_oficial", "tipo_profissional"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    latitude=("latitude", "mean"),
    longitude=("longitude", "mean"),
)

url_brasil = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brasil = gpd.read_file(url_brasil)

fig, axes = plt.subplots(1, 2, figsize=(20, 12))

for idx, tipo in enumerate(["psicologo", "psiquiatra"]):
    ax = axes[idx]
    brasil.plot(ax=ax, color="#f0f0f0", edgecolor="gray")

    df_tipo = df_uf[df_uf["tipo_profissional"] == tipo].copy()

    if df_tipo.empty:
        print(f"❌ Nenhum dado disponível para {tipo}.")
        continue

    gdf = gpd.GeoDataFrame(
        df_tipo,
        geometry=gpd.points_from_xy(df_tipo["longitude"], df_tipo["latitude"]),
        crs="EPSG:4326",
    )

    gdf.plot(
        ax=ax,
        column="preco_medio",
        cmap="viridis",
        markersize=200,
        alpha=0.85,
        edgecolor="black",
        linewidth=1,
        legend=True,
        legend_kwds={"label": f"Preço médio (R$)", "shrink": 0.6},
    )

    ax.set_title(
        f"Preços médios de {tipo.capitalize()} por Estado", fontsize=14, weight="bold"
    )
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)

plt.tight_layout()
os.makedirs("output", exist_ok=True)
plt.savefig("output/mapa_precos_psicologo_psiquiatra_por_uf.png", dpi=200)
plt.close()
print(
    "✅ Mapa comparativo de preços por estado salvo em 'output/mapa_precos_psicologo_psiquiatra_por_uf.png'."
)
