import pandas as pd

# Carregar CSV bruto
df = pd.read_csv("psicologos_boaconsulta_profissionais.csv")

# 1. Filtrar somente quem tem preço
df = df[df["preco"].notna()].copy()

# 2. Manter apenas as colunas de interesse
df = df[["nome", "preco", "cidade", "uf"]]

# 3. Remover duplicados (nome + cidade + uf iguais)
df = df.drop_duplicates(subset=["nome", "cidade", "uf"])

# 4. Opcional: descartar preços muito baixos/altos que parecem erro
df = df[(df["preco"] >= 50) & (df["preco"] <= 1000)]

# 5. Salvar em novo CSV
df.to_csv("psicologos_boaconsulta_precos.csv", index=False, encoding="utf-8-sig")

print("Arquivo limpo salvo como 'psicologos_boaconsulta_precos.csv'")
print(df.head())
print(f"Total de registros com preço válido: {len(df)}")
