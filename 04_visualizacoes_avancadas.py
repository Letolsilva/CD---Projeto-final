#!/usr/bin/env python3
"""
04_visualizacoes_avancadas.py

Visualizações avançadas usando base_precos_mentais_2020_2024.csv:
  1. Correlação entre número de CAPS e casos F32/F41 por município.
  2. Comparação de preços médios entre municípios com e sem CAPS.

Requer:
  - pandas
  - matplotlib
  - seaborn
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_PATH = os.path.join("output", "base_precos_mentais_2020_2024.csv")

# Carregar base
if not os.path.exists(BASE_PATH):
    raise FileNotFoundError(f"Arquivo {BASE_PATH} não encontrado.")
df = pd.read_csv(BASE_PATH, encoding="utf-8-sig")

# 1. Correlação CAPS x casos F32/F41 (por município, média dos anos)
df_caps = df.dropna(subset=["Qtd_caps", "casos_f32_f41"])
df_caps_group = df_caps.groupby(["cidade_oficial", "uf_oficial"], as_index=False).agg(
    casos_f32_f41=("casos_f32_f41", "sum"),
    qtd_caps=("Qtd_caps", "max"),
)
plt.figure(figsize=(7, 5))
sns.scatterplot(
    data=df_caps_group,
    x="qtd_caps",
    y="casos_f32_f41",
    hue="uf_oficial",
)
sns.regplot(
    data=df_caps_group,
    x="qtd_caps",
    y="casos_f32_f41",
    scatter=False,
    color="black",
)
plt.title("Correlação: Nº CAPS x Casos F32/F41 (2020-2024)")
plt.xlabel("Quantidade de CAPS no município")
plt.ylabel("Total de casos F32/F41 (2020-2024)")
plt.tight_layout()
plt.savefig("figuras/scatter_caps_casos.png", dpi=150)
plt.close()
print("Figura salva: figuras/scatter_caps_casos.png")

# 2. Preço médio por município com/sem CAPS (boxplot)
df_caps_flag = df.copy()
df_caps_flag["tem_caps"] = df_caps_flag["Qtd_caps"].fillna(0).astype(int) > 0
plt.figure(figsize=(7, 5))
sns.boxplot(
    data=df_caps_flag,
    x="tem_caps",
    y="preco_medio",
)
plt.xticks([0, 1], ["Sem CAPS", "Com CAPS"])
plt.title("Preço médio da sessão: municípios com vs sem CAPS")
plt.xlabel("Município possui CAPS?")
plt.ylabel("Preço médio da sessão (R$)")
plt.tight_layout()
plt.savefig("figuras/boxplot_preco_caps.png", dpi=150)
plt.close()
print("Figura salva: figuras/boxplot_preco_caps.png")

# 3. Mapa de calor (heatmap) de preços medianos por UF
plt.figure(figsize=(10, 4))
df_uf = df.groupby("uf_oficial")["preco_mediano"].median().reset_index()
df_uf = df_uf.sort_values("preco_mediano", ascending=False)
sns.heatmap(
    df_uf[["preco_mediano"]].T,
    annot=df_uf["preco_mediano"].values.reshape(1, -1),
    fmt=".1f",
    cmap="YlOrRd",
    cbar=True,
    xticklabels=df_uf["uf_oficial"],
    yticklabels=["Preço mediano"],
)
plt.title("Mapa de calor: preço mediano por UF")
plt.tight_layout()
plt.savefig("figuras/heatmap_preco_uf.png", dpi=150)
plt.close()
print("Figura salva: figuras/heatmap_preco_uf.png")

# 4. Boxplot dos preços por faixa de casos F32/F41
faixas = pd.qcut(df["casos_f32_f41"].fillna(0), q=3, labels=["Baixa", "Média", "Alta"])
df_box = df.copy()
df_box["faixa_casos"] = faixas
plt.figure(figsize=(7, 5))
sns.boxplot(
    data=df_box,
    x="faixa_casos",
    y="preco_medio",
)
plt.title("Distribuição do preço médio por faixa de casos F32/F41")
plt.xlabel("Faixa de casos F32/F41 (2020-2024)")
plt.ylabel("Preço médio da sessão (R$)")
plt.tight_layout()
plt.savefig("figuras/boxplot_preco_faixa_casos.png", dpi=150)
plt.close()
print("Figura salva: figuras/boxplot_preco_faixa_casos.png")

# 5. Evolução temporal dos casos F32/F41 vs. preços médios
plt.figure(figsize=(8, 5))
df_evol = (
    df.groupby("ano")
    .agg(
        preco_medio=("preco_medio", "mean"),
        casos_f32_f41=("casos_f32_f41", "sum"),
    )
    .reset_index()
)
ax1 = plt.gca()
color1 = "tab:blue"
color2 = "tab:red"
ax1.set_xlabel("Ano")
ax1.set_ylabel("Preço médio (R$)", color=color1)
ax1.plot(
    df_evol["ano"],
    df_evol["preco_medio"],
    color=color1,
    marker="o",
    label="Preço médio",
)
ax1.tick_params(axis="y", labelcolor=color1)
ax2 = ax1.twinx()
ax2.set_ylabel("Casos F32/F41", color=color2)
ax2.plot(
    df_evol["ano"],
    df_evol["casos_f32_f41"],
    color=color2,
    marker="s",
    label="Casos F32/F41",
)
ax2.tick_params(axis="y", labelcolor=color2)
plt.title("Evolução temporal: preço médio vs casos F32/F41")
plt.tight_layout()
plt.savefig("figuras/evolucao_preco_casos.png", dpi=150)
plt.close()
print("Figura salva: figuras/evolucao_preco_casos.png")

# 6. Relação entre preço médio e quantidade de profissionais
plt.figure(figsize=(7, 5))
df_prof = df.groupby(["cidade_oficial", "uf_oficial"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    qtd_profissionais=("qtd_profissionais", "sum"),
)
sns.scatterplot(
    data=df_prof,
    x="qtd_profissionais",
    y="preco_medio",
    hue="uf_oficial",
)
sns.regplot(
    data=df_prof,
    x="qtd_profissionais",
    y="preco_medio",
    scatter=False,
    color="black",
)
plt.title("Relação: preço médio vs quantidade de profissionais")
plt.xlabel("Quantidade de profissionais no município")
plt.ylabel("Preço médio da sessão (R$)")
plt.tight_layout()
plt.savefig("figuras/scatter_preco_profissionais.png", dpi=150)
plt.close()
print("Figura salva: figuras/scatter_preco_profissionais.png")

# 7. Ranking de municípios por preço, casos e CAPS
rank_cols = ["cidade_oficial", "uf_oficial", "preco_medio", "casos_f32_f41", "Qtd_caps"]
df_rank = df.groupby(["cidade_oficial", "uf_oficial"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    casos_f32_f41=("casos_f32_f41", "sum"),
    Qtd_caps=("Qtd_caps", "max"),
)
# Top 10 por preço
top_preco = df_rank.nlargest(10, "preco_medio")[rank_cols]
# Top 10 por casos
top_casos = df_rank.nlargest(10, "casos_f32_f41")[rank_cols]
# Top 10 por CAPS
top_caps = df_rank.nlargest(10, "Qtd_caps")[rank_cols]
# Salvar como CSV
os.makedirs("figuras", exist_ok=True)
top_preco.to_csv("figuras/ranking_top_preco.csv", index=False, encoding="utf-8-sig")
top_casos.to_csv("figuras/ranking_top_casos.csv", index=False, encoding="utf-8-sig")
top_caps.to_csv("figuras/ranking_top_caps.csv", index=False, encoding="utf-8-sig")
print("\nRanking de municípios por preço médio (top 10):\n", top_preco)
print("\nRanking de municípios por casos F32/F41 (top 10):\n", top_casos)
print("\nRanking de municípios por quantidade de CAPS (top 10):\n", top_caps)
print("Rankings salvos em 'figuras/'.")

print("\n✅ Visualizações avançadas geradas na pasta 'figuras'.")
