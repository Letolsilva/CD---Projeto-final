#!/usr/bin/env python3
"""
08_indice_acessibilidade.py

Cria métricas derivadas:

- indice_carga = casos_f32_f41 / (qtd_profissionais + 1)
  => quantos casos F32/F41 por profissional, aproxima a "pressão" da demanda

- indice_acessibilidade = preco_medio * indice_carga
  => quanto maior, mais cara e mais sobrecarregada parece a oferta
     (ideal para interpretar como "pior acesso")

Entrada: output/base_precos_mentais_2023.csv
Saída:
- output/base_precos_mentais_2023_indice_acessibilidade.csv
- imprime TOP 10 e BOTTOM 10 municípios por acessibilidade (psicólogos)
"""

import os
import pandas as pd

BASE_PATH = "output"
INPUT_FILE = os.path.join(BASE_PATH, "base_precos_mentais_2023.csv")
OUTPUT_FILE = os.path.join(
    BASE_PATH, "base_precos_mentais_2023_indice_acessibilidade.csv"
)


def carregar_base():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    return df


def preparar(df):
    for col in ["preco_medio", "qtd_profissionais", "casos_f32_f41"]:
        if col not in df.columns:
            df[col] = 0.0

    df["preco_medio"] = pd.to_numeric(df["preco_medio"], errors="coerce")
    df["qtd_profissionais"] = pd.to_numeric(df["qtd_profissionais"], errors="coerce")
    df["casos_f32_f41"] = (
        pd.to_numeric(df["casos_f32_f41"], errors="coerce").fillna(0).clip(lower=0)
    )

    # Substituir NaN de profissionais por 0 e garantir >=1 no denominador
    df["qtd_profissionais"] = df["qtd_profissionais"].fillna(0)
    df["denom_prof"] = df["qtd_profissionais"].clip(lower=0) + 1

    df["indice_carga"] = df["casos_f32_f41"] / df["denom_prof"]

    # Índice de acessibilidade: preço * carga
    df["indice_acessibilidade"] = df["preco_medio"] * df["indice_carga"]

    return df


def mostrar_top_bottom(df, tipo, n=10):
    sub = df[df["tipo_profissional"] == tipo].copy()
    sub = sub.dropna(subset=["indice_acessibilidade"])

    if sub.empty:
        print(f"\n⚠️ Sem dados para tipo_profissional = {tipo}")
        return

    sub = sub.sort_values("indice_acessibilidade", ascending=False)

    print(f"\n=== {tipo.upper()} — TOP {n} pior acessibilidade (índice maior) ===")
    cols = [
        "cidade_oficial",
        "uf_oficial",
        "preco_medio",
        "qtd_profissionais",
        "casos_f32_f41",
        "indice_carga",
        "indice_acessibilidade",
    ]
    print(sub[cols].head(n).round(2))

    print(f"\n=== {tipo.upper()} — TOP {n} melhor acessibilidade (índice menor) ===")
    print(sub[cols].tail(n).round(2))


def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_FILE}. Rode antes o 02_mentais_merge_exemplo.py"
        )

    df = carregar_base()
    df = preparar(df)

    os.makedirs(BASE_PATH, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ Base com índices salva em: {OUTPUT_FILE}")

    for tipo in ["psicologo", "psiquiatra"]:
        mostrar_top_bottom(df, tipo, n=10)


if __name__ == "__main__":
    main()
