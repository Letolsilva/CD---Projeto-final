#!/usr/bin/env python3
"""
12_mapa_brasil_interativo.py

Gera um mapa interativo do Brasil por estado, mostrando:
- preço médio psicólogo
- preço médio psiquiatra
- casos F32/F41
- quantidade de CAPS (se existir)

Estados SEM dados continuam aparecendo no mapa,
em cinza claro (camada de fundo).
"""

import os
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.io as pio

# ====================================================================
# CAMINHOS
# ====================================================================
BASE_PRINCIPAL = "output/base_precos_mentais_2020_2024.csv"
PATH_SHAPE = (
    "https://raw.githubusercontent.com/codeforamerica/"
    "click_that_hood/master/public/data/brazil-states.geojson"
)

# ====================================================================
# CARREGAR DADOS PRINCIPAIS
# ====================================================================
print("Carregando base de análise...")
df = pd.read_csv(BASE_PRINCIPAL, encoding="utf-8-sig")
print("Colunas da base:", list(df.columns))

# Se não tiver CAPS, cria coluna com zero
if "Qtd_caps" not in df.columns:
    df["Qtd_caps"] = 0

# Normalizar UF
df["uf_oficial"] = df["uf_oficial"].astype(str).str.upper().str.strip()

# ====================================================================
# AGREGAR POR ESTADO (psicólogo/psiquiatra separados)
# ====================================================================
print("Agregando por estado...")

# preço médio por UF e tipo_profissional
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

# outros agregados (independem do tipo)
outros = df.groupby("uf_oficial").agg(
    casos_F32_F41=("casos_f32_f41", "sum"),
    qtd_profissionais=("qtd_profissionais", "sum"),
    caps_totais=("Qtd_caps", "sum"),
)

agg = precos.join(outros, how="outer").reset_index()

print("Resumo agregado por estado:")
print(agg)

# ====================================================================
# CARREGAR GEOMETRIA DOS ESTADOS
# ====================================================================
print("Carregando geometria dos estados...")
gdf = gpd.read_file(PATH_SHAPE)
print("Colunas do shape:", list(gdf.columns))

# --------------------------------------------------------------------
# DETECTAR COMO PEGAR A SIGLA DE UF NO SHAPE
# --------------------------------------------------------------------
uf_col = None

# 1) Se tiver código direto de UF
for cand in ["state_code", "UF", "uf", "sigla", "code", "id"]:
    if cand in gdf.columns:
        uf_col = cand
        break

# 2) Se não tiver, usar o nome do estado e mapear para sigla
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

# ====================================================================
# MERGE GEO + DADOS
# ====================================================================
mapa = gdf.merge(agg, on="uf_oficial", how="left")

# Marcar se tem dado ou não
mapa["tem_dado"] = ~mapa["preco_psicologo"].isna()

# ====================================================================
# CAMADA 1 – mapa de fundo (todos os estados em cinza claro)
# ====================================================================
fig_base = px.choropleth(
    mapa,
    geojson=mapa.geometry,
    locations=mapa.index,
    color_discrete_sequence=["#e0e0e0"],  # cinza clarinho
    hover_name="uf_oficial",
    hover_data={},  # sem dados no hover da camada de fundo
)

fig_base.update_traces(
    marker_line_color="white",
    marker_line_width=0.5,
    showlegend=False,
)

fig_base.update_geos(fitbounds="locations", visible=False)

# ====================================================================
# CAMADA 2 – estados com dados (coloridos pelo preço do psicólogo)
# ====================================================================
mapa_com_dado = mapa[mapa["tem_dado"]].copy()

fig_dados = px.choropleth(
    mapa_com_dado,
    geojson=mapa_com_dado.geometry,
    locations=mapa_com_dado.index,
    color="preco_psicologo",
    projection="mercator",
    hover_name="uf_oficial",
    hover_data={
        "preco_psicologo": ":.2f",  # 2 casas decimais
        "preco_psiquiatra": ":.2f",
        "casos_F32_F41": ":,",  # separador de milhar
        "caps_totais": ":,",
        "qtd_profissionais": ":,",
    },
    color_continuous_scale="Blues",  # <-- tons de azul padrão do Plotly
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


# ====================================================================
# JUNTAR AS DUAS CAMADAS
# ====================================================================
# adiciona o trace com os dados
fig_base.add_trace(fig_dados.data[0])

# copia também o coloraxis (onde está a escala azul!)
fig_base.update_layout(
    coloraxis=fig_dados.layout.coloraxis,
    title="Preço médio de Psicólogos por Estado (com dados de saúde mental)",
    hoverlabel=dict(
        bgcolor="white",
        font_size=12,
        font_family="Arial",
    ),
)


# ====================================================================
# GERAR HTML COM BORDA ARREDONDADA NO CARD DE HOVER
# ====================================================================
os.makedirs("output", exist_ok=True)
out_path = os.path.join("output", "mapa_preco_psicologo_brasil.html")

# Gera o HTML como string
html = pio.to_html(fig_base, full_html=True)

# JS pra deixar os cards de hover com bordas arredondadas
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
    // chama ao carregar e sempre que o mouse mexer (hover novo)
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
