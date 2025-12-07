#!/usr/bin/env python3

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PATH_CAPS = "t_mentais_datasus-main/CAPS_Municipios.csv"

if not os.path.exists(PATH_CAPS):
    raise FileNotFoundError("Arquivo CAPS_Municipios.csv não encontrado.")

caps = pd.read_csv(PATH_CAPS, encoding="utf-8")
print("Colunas lidas:", list(caps.columns))

caps_city = (
    caps.groupby(["Município", "UF"], as_index=False)["Qtd_caps"]
    .sum()
    .rename(columns={"Qtd_caps": "qtd_caps"})
    .sort_values("qtd_caps", ascending=False)
)

print(caps_city.head())

os.makedirs("figuras", exist_ok=True)

sns.set(style="whitegrid")
plt.figure(figsize=(10, 6))

ax = sns.barplot(data=caps_city, x="UF", y="qtd_caps", color="#4C72B0")

plt.title("Número de CAPS por UF")
plt.xlabel("UF")
plt.ylabel("Quantidade de CAPS")

for p in ax.patches:
    height = p.get_height()
    ax.annotate(
        f"{int(height)}",
        (p.get_x() + p.get_width() / 2.0, height),
        ha="center",
        va="bottom",
        fontsize=9,
    )

plt.tight_layout()

out_path = "figuras/bar_caps_por_cidade.png"
plt.figure(figsize=(12, 8))
ax = sns.barplot(
    data=caps_city.head(20), x="qtd_caps", y="Município", hue="UF", dodge=False
)
plt.title("Número de CAPS por cidade (Top 20)")
plt.xlabel("Quantidade de CAPS")
plt.ylabel("Cidade")
plt.legend(title="UF", bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()
plt.savefig(out_path, dpi=150)
plt.close()
print(f"Figura salva: {out_path}")
