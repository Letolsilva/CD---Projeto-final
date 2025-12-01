#!/usr/bin/env python3
"""
09_mapa_precos_psicologos_psiquiatras_por_municipio.py

Gera mapas de dispersão geográfica dos preços médios de psicólogos e psiquiatras por município.
Cada ponto representa um município, colorido conforme o preço médio.

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

# Caminhos dos arquivos
PATH_PRECOS = "output/precos_por_municipio.csv"
PATH_MUN = "t_mentais_datasus-main/BR_Municipios_2023.csv"

# Carregar municípios (com lat/lon)
mun = pd.read_csv(PATH_MUN, encoding="utf-8")
mun["codigo_ibge"] = mun["codigo_ibge"].astype(str).str.zfill(7)
mun["nome_norm"] = mun["nome"].apply(lambda x: unidecode(str(x)).lower())

# Carregar preços
precos = pd.read_csv(PATH_PRECOS, encoding="utf-8")
precos["cidade_norm"] = precos["cidade_norm"].apply(lambda x: unidecode(str(x)).lower())

# Função para gerar mapa


def plot_mapa_precos(tipo, preco_col, output_file):
    df = precos[precos["tipo_profissional"] == tipo].copy()
    df = df.merge(mun, left_on="cidade_norm", right_on="nome_norm", how="left")
    df = df.dropna(subset=["latitude", "longitude", preco_col])
    if df.empty:
        print(f"❌ Nenhum dado disponível para {tipo}.")
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
    # Plotar pontos coloridos pelo preço
    gdf.plot(
        ax=ax,
        column=preco_col,
        cmap="viridis",
        markersize=40,
        alpha=0.85,
        edgecolor="black",
        linewidth=0.5,
        legend=True,
        legend_kwds={"label": f"Preço médio de {tipo} (R$)", "shrink": 0.6},
    )
    plt.title(f"Dispersão geográfica dos preços médios de {tipo}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    os.makedirs("output", exist_ok=True)
    plt.savefig(output_file, dpi=200)
    plt.close()
    print(f"✅ Mapa de preços de {tipo} salvo em '{output_file}'.")


# Psicólogos
plot_mapa_precos(
    "psicologo", "preco_medio", "output/mapa_precos_psicologos_por_municipio.png"
)
# Psiquiatras
plot_mapa_precos(
    "psiquiatra", "preco_medio", "output/mapa_precos_psiquiatras_por_municipio.png"
)
