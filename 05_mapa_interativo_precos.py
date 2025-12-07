#!/usr/bin/env python3

import os
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.io as pio

BASE_PRINCIPAL = "output/base_precos_mentais_2020_2024.csv"
PATH_SHAPE = (
    "https://raw.githubusercontent.com/codeforamerica/"
    "click_that_hood/master/public/data/brazil-states.geojson"
)

print("Carregando base de análise...")
df = pd.read_csv(BASE_PRINCIPAL, encoding="utf-8-sig")
print("Colunas da base:", list(df.columns))

if "Qtd_caps" not in df.columns:
    df["Qtd_caps"] = 0

df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()

print("Agregando por estado...")

precos = (
    df.groupby(["uf_oficial", "tipo_profissional"])["preco_medio"]
    .mean()
    .reset_index()
    .pivot(index="uf_oficial", columns="tipo_profissional", values="preco_medio")
    .rename(
        columns={
            "psicologo": "preco_psicologo",
            "psiquiatra": "preco_psiquiatra",
        }
    )
)

outros = df.groupby("uf_oficial").agg(
    casos_F32_F41=("casos_f32_f41", "sum"),
    qtd_profissionais=("qtd_profissionais", "sum"),
    caps_totais=("Qtd_caps", "sum"),
)

agg = precos.join(outros, how="outer").reset_index()

print("Resumo agregado por estado:")
print(agg)

print("Carregando geometria dos estados...")
gdf = gpd.read_file(PATH_SHAPE)
print("Colunas do shape:", list(gdf.columns))

uf_col = None

for cand in ["state_code", "UF", "uf", "sigla", "code", "id"]:
    if cand in gdf.columns:
        uf_col = cand
        break

if uf_col is None:
    if "name" not in gdf.columns:
        raise ValueError(
            "Não encontrei coluna de UF nem 'name' no GeoJSON. "
            "Veja as colunas impressas acima."
        )
    print("Usando coluna 'name' do shape e mapeando para sigla de UF...")
    name_to_uf = {
        "Acre": "AC",
        "Alagoas": "AL",
        "Amapá": "AP",
        "Amazonas": "AM",
        "Bahia": "BA",
        "Ceará": "CE",
        "Distrito Federal": "DF",
        "Espírito Santo": "ES",
        "Goiás": "GO",
        "Maranhão": "MA",
        "Mato Grosso": "MT",
        "Mato Grosso do Sul": "MS",
        "Minas Gerais": "MG",
        "Pará": "PA",
        "Paraíba": "PB",
        "Paraná": "PR",
        "Pernambuco": "PE",
        "Piauí": "PI",
        "Rio de Janeiro": "RJ",
        "Rio Grande do Norte": "RN",
        "Rio Grande do Sul": "RS",
        "Rondônia": "RO",
        "Roraima": "RR",
        "Santa Catarina": "SC",
        "São Paulo": "SP",
        "Sergipe": "SE",
        "Tocantins": "TO",
    }
    gdf["uf_oficial"] = gdf["name"].map(name_to_uf)
else:
    gdf["uf_oficial"] = gdf[uf_col].astype(str).str.upper().str.strip()

print("Exemplo de UF no shape:")
print(gdf[["uf_oficial"]].head())

mapa = gdf.merge(agg, on="uf_oficial", how="left")

mapa["tem_dado"] = ~mapa["preco_psicologo"].isna()

fig_base = px.choropleth(
    mapa,
    geojson=mapa.geometry,
    locations=mapa.index,
    color_discrete_sequence=["#e0e0e0"],
    hover_name="uf_oficial",
    hover_data={},
)

fig_base.update_traces(
    marker_line_color="white",
    marker_line_width=0.5,
    showlegend=False,
)

fig_base.update_geos(fitbounds="locations", visible=False)

mapa_com_dado = mapa[mapa["tem_dado"]].copy()

fig_dados = px.choropleth(
    mapa_com_dado,
    geojson=mapa_com_dado.geometry,
    locations=mapa_com_dado.index,
    color="preco_psicologo",
    projection="mercator",
    hover_name="uf_oficial",
    hover_data={
        "preco_psicologo": ":.2f",
        "preco_psiquiatra": ":.2f",
        "casos_F32_F41": ":,",
        "caps_totais": ":,",
        "qtd_profissionais": ":,",
    },
    color_continuous_scale="Blues",
    labels={
        "preco_psicologo": "Preço médio psicólogo (R$)",
        "preco_psiquiatra": "Preço médio psiquiatra (R$)",
        "casos_F32_F41": "Casos F32/F41",
        "caps_totais": "Total de CAPS",
        "qtd_profissionais": "Qtd. de profissionais",
    },
)
fig_dados.layout.coloraxis.colorbar.title = "Preço médio psicólogo (R$)"

fig_dados.update_traces(
    marker_line_color="white",
    marker_line_width=0.5,
    showlegend=False,
)

fig_base.add_trace(fig_dados.data[0])

fig_base.update_layout(
    coloraxis=fig_dados.layout.coloraxis,
    title="Preço médio de Psicólogos por Estado (com dados de saúde mental)",
    hoverlabel=dict(
        bgcolor="white",
        font_size=12,
        font_family="Arial",
    ),
)

os.makedirs("output", exist_ok=True)
out_path = os.path.join("output", "mapa_preco_psicologo_brasil.html")

html = pio.to_html(fig_base, full_html=True)

extra_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    function arredondaHover() {
        const rects = document.querySelectorAll('.hoverlayer .bg');
        rects.forEach(function(r) {
            r.setAttribute('rx', 8);
            r.setAttribute('ry', 8);
        });
    }
    arredondaHover();
    document.addEventListener('mousemove', arredondaHover);
});
</script>
"""

html = html.replace("</body>", extra_js + "\\n</body>")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Mapa salvo em: {out_path}")
print("Abra esse arquivo no navegador (Chrome/Edge/etc.).")
