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

# Arquivos de notificações
anos = ["20", "21", "22", "23", "24"]
mentais_files = [f"t_mentais_datasus-main/MENTBR{ano}.csv" for ano in anos]
PATH_MUN = "t_mentais_datasus-main/BR_Municipios_2023.csv"

# Carregar municípios (com lat/lon)
mun = pd.read_csv(PATH_MUN, encoding="utf-8")
mun["codigo_ibge"] = mun["codigo_ibge"].astype(str).str.zfill(7)

# Carregar e consolidar notificações
casos = []
for path in mentais_files:
    df = pd.read_csv(path, encoding="utf-8")
    # Filtrar F32 e F41
    df = df[df["DIAG_ESP"].isin(["F32", "F41"])]
    # Normalizar código IBGE
    df["ID_MUNICIP"] = df["ID_MUNICIP"].astype(str).str.zfill(7)
    casos.append(df)
casos_df = pd.concat(casos, ignore_index=True)

# Função para gerar mapa individual


def plot_mapa_casos_individual(diag, output_file):
    df = casos_df[casos_df["DIAG_ESP"] == diag].copy()
    df = df.merge(mun, left_on="ID_MUNICIP", right_on="codigo_ibge", how="left")
    df = df.dropna(subset=["latitude", "longitude"])
    if df.empty:
        print(f"❌ Nenhum dado disponível para {diag}.")
        return
    # Criar GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    # Mapa base do Brasil
    url_brasil = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    brasil = gpd.read_file(url_brasil)
    fig, ax = plt.subplots(figsize=(10, 12))
    brasil.plot(ax=ax, color="#f0f0f0", edgecolor="gray")
    # Plotar cada caso como ponto individual
    gdf.plot(
        ax=ax,
        markersize=18,
        color="#1976d2",
        alpha=0.7,
        edgecolor="black",
        linewidth=0.2,
        label=f"Casos de {diag}",
    )
    plt.title(f"Dispersão geográfica dos casos individuais de {diag}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.tight_layout()
    os.makedirs("output", exist_ok=True)
    plt.savefig(output_file, dpi=200)
    plt.close()
    print(f"✅ Mapa de casos individuais de {diag} salvo em '{output_file}'.")


# F32
plot_mapa_casos_individual("F32", "output/mapa_casos_f32_individual.png")
# F41
plot_mapa_casos_individual("F41", "output/mapa_casos_f41_individual.png")
