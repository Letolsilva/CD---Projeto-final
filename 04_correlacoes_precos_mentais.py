#!/usr/bin/env python3
"""
04_correlacoes_precos_mentais.py

Gera gráficos de correlação entre:
- preço médio da sessão (preco_medio)
- número de casos F32/F41 (casos_f32_f41)

Usa:
  output/base_precos_mentais_2023.csv
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_PATH = "output"
INPUT_BASE = os.path.join(BASE_PATH, "base_precos_mentais_2023.csv")


def carregar_base():
    if not os.path.exists(INPUT_BASE):
        raise FileNotFoundError(
            f"Arquivo {INPUT_BASE} não encontrado. "
            "Certifique-se de ter rodado antes o 02_mentais_merge_exemplo.py."
        )
    df = pd.read_csv(INPUT_BASE, encoding="utf-8-sig")
    print("Colunas da base:", list(df.columns))
    return df


def scatter_preco_vs_casos(df, tipo, fname_suffix):
    sub = df[df["tipo_profissional"] == tipo].copy()
    sub = sub.dropna(subset=["preco_medio"])
    sub["casos_f32_f41"] = sub["casos_f32_f41"].fillna(0)

    if sub.empty:
        print(f"⚠️ Nenhum dado para {tipo} em scatter.")
        return

    plt.figure(figsize=(7, 5))
    plt.scatter(sub["preco_medio"], sub["casos_f32_f41"])
    plt.title(f"Preço médio x Casos F32/F41 – {tipo} (2023)")
    plt.xlabel("Preço médio da sessão (R$)")
    plt.ylabel("Casos F32/F41 no município (2023)")
    plt.tight_layout()

    os.makedirs(BASE_PATH, exist_ok=True)
    out = os.path.join(BASE_PATH, f"scatter_preco_vs_casos_{fname_suffix}.png")
    plt.savefig(out, dpi=300)
    print(f"✅ Scatter salvo em {out}")

    plt.show()


def matriz_correlacao(df, tipo, fname_suffix):
    sub = df[df["tipo_profissional"] == tipo].copy()
    sub = sub.dropna(subset=["preco_medio"])
    sub["casos_f32_f41"] = sub["casos_f32_f41"].fillna(0)

    if sub.empty:
        print(f"⚠️ Nenhum dado para {tipo} em correlação.")
        return

    cols = ["preco_medio", "casos_f32_f41"]
    corr = sub[cols].corr()
    print(f"\nMatriz de correlação ({tipo}):")
    print(corr)

    plt.figure(figsize=(4, 4))
    plt.imshow(corr.values, aspect="auto")
    plt.xticks(range(len(cols)), cols, rotation=45, ha="right")
    plt.yticks(range(len(cols)), cols)
    plt.colorbar()
    plt.title(f"Matriz de correlação – {tipo}")
    plt.tight_layout()

    out = os.path.join(BASE_PATH, f"correlacao_matriz_{fname_suffix}.png")
    plt.savefig(out, dpi=300)
    print(f"✅ Matriz de correlação salva em {out}")

    plt.show()


def main():
    df = carregar_base()

    # Psicólogos
    scatter_preco_vs_casos(df, tipo="psicologo", fname_suffix="psicologos")
    matriz_correlacao(df, tipo="psicologo", fname_suffix="psicologos")

    # Psiquiatras
    scatter_preco_vs_casos(df, tipo="psiquiatra", fname_suffix="psiquiatras")
    matriz_correlacao(df, tipo="psiquiatra", fname_suffix="psiquiatras")


if __name__ == "__main__":
    main()
