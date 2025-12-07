#!/usr/bin/env python3
"""
11_mapa_casos_f32_f41_individual.py

Gera mapas de dispersão geográfica dos casos individuais de F32 (depressão) e F41 (ansiedade).
Cada ponto representa um caso (linha) encontrado nos arquivos MENTBRxx.

Requer:
  - pandas
  - matplotlib
  - geopandas
  - unidecode

Salva os gráficos como PNG em 'output/'.
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from unidecode import unidecode

anos = ["20", "21", "22", "23", "24"]
mentais_files = [f"t_mentais_datasus-main/MENTBR{ano}.csv" for ano in anos]
PATH_MUN = "t_mentais_datasus-main/BR_Municipios_2023.csv"

mun = pd.read_csv(PATH_MUN, encoding="utf-8")
mun["codigo_ibge"] = mun["codigo_ibge"].astype(str).str.zfill(7)

casos = []
for path in mentais_files:
    df = pd.read_csv(path, encoding="utf-8")

    df = df[df["DIAG_ESP"].str.startswith(("F32", "F41"), na=False)]

    df["ID_MUNICIP"] = df["ID_MUNICIP"].astype(str).str.zfill(7)
    casos.append(df)
casos_df = pd.concat(casos, ignore_index=True)


def plot_mapa_casos_individual(diag, output_file):
    df = casos_df[casos_df["DIAG_ESP"].str.startswith(diag, na=False)].copy()
    print(f"\n📊 Total de casos de {diag}* nos arquivos: {len(df)}")

    df = df.merge(mun, left_on="ID_MUNICIP", right_on="codigo_ibge", how="left")
    df = df.dropna(subset=["latitude", "longitude"])
    print(f"📍 Casos com coordenadas válidas: {len(df)}")

    if df.empty:
        print(f"❌ Nenhum dado disponível para {diag}.")
        return

    df_agg = (
        df.groupby(["codigo_ibge", "latitude", "longitude", "nome"], as_index=False)
        .size()
        .rename(columns={"size": "num_casos"})
    )
    print(f"🏙️  Municípios únicos com casos: {len(df_agg)}")
    print(f"🔝 Top 5 municípios com mais casos:")
    print(df_agg.nlargest(5, "num_casos")[["nome", "num_casos"]])

    gdf = gpd.GeoDataFrame(
        df_agg,
        geometry=gpd.points_from_xy(df_agg["longitude"], df_agg["latitude"]),
        crs="EPSG:4326",
    )

    url_brasil = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    brasil = gpd.read_file(url_brasil)
    fig, ax = plt.subplots(figsize=(10, 12))
    brasil.plot(ax=ax, color="#f0f0f0", edgecolor="gray")

    tamanhos = gdf["num_casos"] * 2 + 30
    gdf.plot(
        ax=ax,
        markersize=tamanhos,
        color="#1976d2",
        alpha=0.6,
        edgecolor="black",
        linewidth=0.3,
        label=f"Casos de {diag}",
    )

    plt.title(
        f"Dispersão geográfica dos casos de {diag} por município\n(tamanho proporcional ao número de casos)"
    )
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.tight_layout()
    os.makedirs("output", exist_ok=True)
    plt.savefig(output_file, dpi=200)
    plt.close()
    print(f"✅ Mapa de casos de {diag} salvo em '{output_file}'.\n")


# F32
plot_mapa_casos_individual("F32", "output/mapa_casos_f32_individual.png")
# F41
plot_mapa_casos_individual("F41", "output/mapa_casos_f41_individual.png")
