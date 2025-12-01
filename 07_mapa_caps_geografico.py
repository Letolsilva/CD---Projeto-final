#!/usr/bin/env python3
"""
07_mapa_caps_geografico.py

Gera um mapa de dispersão geográfica dos CAPS no Brasil.
Cada ponto representa um CAPS, usando latitude/longitude dos municípios.

Requer:
  - pandas
  - matplotlib
  - geopandas

Salva o gráfico como 'output/mapa_caps_geografico.png'.
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# Caminhos dos arquivos
PATH_CAPS = "t_mentais_datasus-main/CAPS_Municipios.csv"
PATH_MUN = "t_mentais_datasus-main/BR_Municipios_2023.csv"

if not os.path.exists(PATH_CAPS) or not os.path.exists(PATH_MUN):
    raise FileNotFoundError(
        "Arquivo CAPS_Municipios.csv ou BR_Municipios_2023.csv não encontrado."
    )

# Carregar CAPS
caps = pd.read_csv(PATH_CAPS, encoding="latin1")
caps["IBGE"] = caps["IBGE"].astype(str).str.zfill(7)

# Carregar municípios (com lat/lon)
mun = pd.read_csv(PATH_MUN, encoding="utf-8")
mun["codigo_ibge"] = mun["codigo_ibge"].astype(str).str.zfill(7)

# Merge CAPS + municípios para pegar lat/lon
caps_geo = caps.merge(mun, left_on="IBGE", right_on="codigo_ibge", how="left")

# Filtrar apenas municípios com lat/lon
caps_geo = caps_geo.dropna(subset=["latitude", "longitude"])

# Criar GeoDataFrame
gdf_caps = gpd.GeoDataFrame(
    caps_geo,
    geometry=gpd.points_from_xy(caps_geo["longitude"], caps_geo["latitude"]),
    crs="EPSG:4326",
)

# Plotar mapa base do Brasil
fig, ax = plt.subplots(figsize=(10, 12))
# Usar GeoJSON do IBGE para o Brasil
url_brasil = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brasil = gpd.read_file(url_brasil)
brasil.plot(ax=ax, color="#f0f0f0", edgecolor="gray")

# Plotar CAPS
gdf_caps.plot(ax=ax, markersize=30, color="#1976d2", alpha=0.7, label="CAPS")

plt.title("Dispersão geográfica dos CAPS no Brasil")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.tight_layout()

os.makedirs("output", exist_ok=True)
plt.savefig("output/mapa_caps_geografico.png", dpi=200)
plt.close()
print("✅ Mapa de dispersão dos CAPS salvo em 'output/mapa_caps_geografico.png'.")
