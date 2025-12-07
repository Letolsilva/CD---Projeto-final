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

    if "casos_f32_f41" in df.columns:
        df["casos_f32_f41"] = df["casos_f32_f41"].fillna(0)

    df = df[df["preco_medio"].notna()].copy()

    os.makedirs("figuras", exist_ok=True)

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

    if "tipo_profissional" in df.columns:
        df_psico = df[df["tipo_profissional"] == "psicologo"].copy()
    else:
        df_psico = df.copy()

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

    if "Qtd_caps" in df.columns:
        df_caps_uf = (
            df.groupby("uf_oficial", as_index=False)
            .agg(
                preco_medio=("preco_medio", "mean"),
                qtd_caps=("Qtd_caps", "sum"),
            )
            .dropna(subset=["qtd_caps"])
        )

        if not df_caps_uf.empty:
            plt.figure(figsize=(8, 6))
            sns.scatterplot(
                data=df_caps_uf,
                x="qtd_caps",
                y="preco_medio",
                hue="uf_oficial",
                s=150,
                alpha=0.7,
                legend="full",
            )
            sns.regplot(
                data=df_caps_uf,
                x="qtd_caps",
                y="preco_medio",
                scatter=False,
                color="black",
                line_kws={"linewidth": 1.5, "linestyle": "--"},
            )
            plt.title("CAPS x preço médio da sessão por Estado")
            plt.xlabel("Total de CAPS no estado")
            plt.ylabel("Preço médio da sessão (R$)")
            plt.legend(
                title="Estado",
                bbox_to_anchor=(1.05, 1),
                loc="upper left",
                ncol=2,
                fontsize=8,
            )
            plt.tight_layout()
            plt.savefig("figuras/scatter_caps_preco_por_uf.png", dpi=150)
            plt.close()
            print("Figura salva: figuras/scatter_caps_preco_por_uf.png")
        else:
            print("Nenhum dado de CAPS válido para scatter.")

    if "casos_f32_f41" in df.columns:
        df_casos_uf = df.groupby("uf_oficial", as_index=False).agg(
            preco_medio=("preco_medio", "mean"),
            casos_f32_f41=("casos_f32_f41", "sum"),
        )

        plt.figure(figsize=(8, 6))
        sns.scatterplot(
            data=df_casos_uf,
            x="casos_f32_f41",
            y="preco_medio",
            hue="uf_oficial",
            s=150,
            alpha=0.7,
            legend="full",
        )
        sns.regplot(
            data=df_casos_uf,
            x="casos_f32_f41",
            y="preco_medio",
            scatter=False,
            color="black",
            line_kws={"linewidth": 1.5, "linestyle": "--"},
        )
        plt.title("Casos F32/F41 x preço médio por Estado")
        plt.xlabel("Total de casos F32/F41 no estado (2020-2024)")
        plt.ylabel("Preço médio da sessão (R$)")
        plt.legend(
            title="Estado",
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
            ncol=2,
            fontsize=8,
        )
        plt.tight_layout()
        plt.savefig("figuras/scatter_casos_preco_por_uf.png", dpi=150)
        plt.close()
        print("Figura salva: figuras/scatter_casos_preco_por_uf.png")

    if "qtd_profissionais" in df.columns:
        df_prof_uf = df.groupby("uf_oficial", as_index=False).agg(
            preco_medio=("preco_medio", "mean"),
            qtd_profissionais=("qtd_profissionais", "sum"),
        )

        plt.figure(figsize=(8, 6))
        sns.scatterplot(
            data=df_prof_uf,
            x="qtd_profissionais",
            y="preco_medio",
            hue="uf_oficial",
            s=150,
            alpha=0.7,
            legend="full",
        )
        sns.regplot(
            data=df_prof_uf,
            x="qtd_profissionais",
            y="preco_medio",
            scatter=False,
            color="black",
            line_kws={"linewidth": 1.5, "linestyle": "--"},
        )
        plt.title("Preço médio x Quantidade de profissionais por Estado")
        plt.xlabel("Total de profissionais no estado")
        plt.ylabel("Preço médio da sessão (R$)")
        plt.legend(
            title="Estado",
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
            ncol=2,
            fontsize=8,
        )
        plt.tight_layout()
        plt.savefig("figuras/scatter_preco_profissionais_por_uf.png", dpi=150)
        plt.close()
        print("Figura salva: figuras/scatter_preco_profissionais_por_uf.png")

    print("\n✅ Visualizações geradas na pasta 'figuras/'.")


if __name__ == "__main__":
    main()
