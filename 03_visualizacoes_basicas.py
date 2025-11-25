#!/usr/bin/env python3
"""
03_visualizacoes_basicas.py

Gera alguns gráficos exploratórios a partir de:
  output/base_precos_mentais_2020_2024.csv

Requer:
  - pandas
  - matplotlib
  - seaborn
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Caminho da base integrada
BASE_PATH = os.path.join("output", "base_precos_mentais_2020_2024.csv")


def main():
    if not os.path.exists(BASE_PATH):
        raise FileNotFoundError(
            f"Arquivo {BASE_PATH} não encontrado. "
            "Confere se o 02_mentais_merge_exemplo.py rodou certinho."
        )

    df = pd.read_csv(BASE_PATH, encoding="utf-8-sig")
    print("Colunas da base integrada:", list(df.columns))
    print("Primeiras linhas:\n", df.head())

    # Alguns ajustes básicos
    if "casos_f32_f41" in df.columns:
        df["casos_f32_f41"] = df["casos_f32_f41"].fillna(0)

    # Filtrar linhas com preço válido
    df = df[df["preco_medio"].notna()].copy()

    # Cria pasta para figuras
    os.makedirs("figuras", exist_ok=True)

    # --------------------------------------------------------
    # 1) Boxplot de preço por tipo de profissional
    # --------------------------------------------------------
    if "tipo_profissional" in df.columns:
        plt.figure(figsize=(8, 5))
        sns.boxplot(
            data=df,
            x="tipo_profissional",
            y="preco_medio",
        )
        plt.title("Distribuição do preço médio por tipo de profissional")
        plt.xlabel("Tipo de profissional")
        plt.ylabel("Preço médio da sessão (R$)")
        plt.tight_layout()
        plt.savefig("figuras/boxplot_preco_por_tipo.png", dpi=150)
        plt.close()
        print("Figura salva: figuras/boxplot_preco_por_tipo.png")

    # --------------------------------------------------------
    # 2) Barras: preço médio por cidade (psicólogos)
    # --------------------------------------------------------
    if "tipo_profissional" in df.columns:
        df_psico = df[df["tipo_profissional"] == "psicologo"].copy()
    else:
        df_psico = df.copy()

    # ordenar cidades pelo preço médio
    df_psico_city = (
        df_psico.groupby(["cidade_oficial", "uf_oficial"], as_index=False)[
            "preco_medio"
        ]
        .mean()
        .sort_values("preco_medio", ascending=False)
    )

    plt.figure(figsize=(8, 5))
    sns.barplot(
        data=df_psico_city,
        x="preco_medio",
        y="cidade_oficial",
        hue="uf_oficial",
        dodge=False,
    )
    plt.title("Preço médio da sessão de psicólogo por cidade")
    plt.xlabel("Preço médio (R$)")
    plt.ylabel("Cidade")
    plt.legend(title="UF", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig("figuras/bar_preco_psicologo_por_cidade.png", dpi=150)
    plt.close()
    print("Figura salva: figuras/bar_preco_psicologo_por_cidade.png")

    # --------------------------------------------------------
    # 3) Barras: quantidade de profissionais por cidade
    # --------------------------------------------------------
    if "qtd_profissionais" in df.columns:
        df_qtd = (
            df.groupby(["cidade_oficial", "uf_oficial"], as_index=False)[
                "qtd_profissionais"
            ]
            .sum()
            .sort_values("qtd_profissionais", ascending=False)
        )

        plt.figure(figsize=(8, 5))
        sns.barplot(
            data=df_qtd,
            x="qtd_profissionais",
            y="cidade_oficial",
            hue="uf_oficial",
            dodge=False,
        )
        plt.title("Quantidade de profissionais cadastrados por cidade")
        plt.xlabel("Nº de profissionais (todas as fontes)")
        plt.ylabel("Cidade")
        plt.legend(title="UF", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()
        plt.savefig("figuras/bar_qtd_prof_por_cidade.png", dpi=150)
        plt.close()
        print("Figura salva: figuras/bar_qtd_prof_por_cidade.png")

    # --------------------------------------------------------
    # 4) Se houver CAPS: relação CAPS x preço médio
    # --------------------------------------------------------
    if "Qtd_caps" in df.columns:
        df_caps = (
            df.groupby(["cidade_oficial", "uf_oficial"], as_index=False)
            .agg(
                preco_medio=("preco_medio", "mean"),
                qtd_caps=("Qtd_caps", "max"),  # assume valor único por município
            )
            .dropna(subset=["qtd_caps"])
        )

        if not df_caps.empty:
            plt.figure(figsize=(6, 5))
            sns.scatterplot(
                data=df_caps,
                x="qtd_caps",
                y="preco_medio",
                hue="uf_oficial",
            )
            plt.title("CAPS x preço médio da sessão (por município)")
            plt.xlabel("Quantidade de CAPS no município")
            plt.ylabel("Preço médio da sessão (R$)")
            plt.tight_layout()
            plt.savefig("figuras/scatter_caps_preco.png", dpi=150)
            plt.close()
            print("Figura salva: figuras/scatter_caps_preco.png")
        else:
            print("Nenhum dado de CAPS válido para scatter.")

    # --------------------------------------------------------
    # 5) (Quando tivermos casos_f32_f41 != 0)
    #    Scatter preço x casos de transtornos
    # --------------------------------------------------------
    if "casos_f32_f41" in df.columns:
        df_casos = df.groupby(["cidade_oficial", "uf_oficial"], as_index=False).agg(
            preco_medio=("preco_medio", "mean"),
            casos_f32_f41=("casos_f32_f41", "sum"),
        )

        # mesmo se tudo for zero, gera o gráfico (vai virar uma linha no eixo X)
        plt.figure(figsize=(6, 5))
        sns.scatterplot(
            data=df_casos,
            x="casos_f32_f41",
            y="preco_medio",
        )
        plt.title("Casos F32/F41 x preço médio (por município)")
        plt.xlabel("Nº de casos F32/F41 (2020-2024)")
        plt.ylabel("Preço médio da sessão (R$)")
        plt.tight_layout()
        plt.savefig("figuras/scatter_casos_preco.png", dpi=150)
        plt.close()
        print("Figura salva: figuras/scatter_casos_preco.png")

    print("\n✅ Visualizações geradas na pasta 'figuras/'.")


if __name__ == "__main__":
    main()
