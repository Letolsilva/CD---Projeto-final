import pandas as pd

df = pd.read_csv("output/base_precos_mentais_2020_2024.csv", encoding="utf-8-sig")

df_city = df.groupby(["cidade_oficial", "uf_oficial"], as_index=False).agg(
    preco_medio=("preco_medio", "mean"),
    casos_f32_f41=("casos_f32_f41", "sum"),
    qtd_caps=("Qtd_caps", "max"),
)

df_city = df_city.sort_values("preco_medio", ascending=False).head(20)

print("Top 20 cidades por preço médio:")
print(df_city.to_string(index=False))

print("\n\nTabela LaTeX:")
print("\\begin{table}[h]")
print("\\centering")
print("\\caption{Resumo de preço médio, CAPS e casos F32/F41 por cidade (2020-2024).}")
print("\\label{tab_preco_resumo_cidade}")
print("\\begin{tabular}{lcccc}")
print("\\hline")
print(
    "\\textbf{Cidade} & \\textbf{UF} & \\textbf{Preço médio (R\\$)} & \\textbf{Casos F32/F41} & \\textbf{Qtd. CAPS} \\\\"
)
print("\\hline")

for _, row in df_city.iterrows():
    if pd.isna(row["qtd_caps"]):
        continue

    cidade = row["cidade_oficial"]
    uf = row["uf_oficial"]
    preco = row["preco_medio"]
    casos = int(row["casos_f32_f41"])
    caps = int(row["qtd_caps"])

    preco_str = f"{preco:.2f}".replace(".", "{,}")

    print(f"{cidade:20s} & {uf:2s} & {preco_str} & {casos:4d} & {caps:2d} \\\\")

print("\\hline")
print("\\end{tabular}")
print("\\end{table}")
