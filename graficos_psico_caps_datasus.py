#!/usr/bin/env python3
"""
Gera gráficos a partir de summary_precos_caps_transtornos_por_UF.csv

Requer:
    pip install matplotlib pandas
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(".").resolve()
SUMMARY_PATH = BASE_DIR / "summary_precos_caps_transtornos_por_UF.csv"


def load_summary():
    df = pd.read_csv(SUMMARY_PATH, encoding="utf-8-sig")
    return df


def grafico_preco_mediano_por_uf(df: pd.DataFrame):
    """
    Barplot: preço mediano de consulta psicológica por UF
    """
    data = df.sort_values("preco_mediano", ascending=False)

    plt.figure(figsize=(10, 6))
    plt.bar(data["UF"], data["preco_mediano"])
    plt.title("Preço mediano de consulta psicológica por UF")
    plt.xlabel("UF")
    plt.ylabel("Preço mediano (R$)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("graf_preco_mediano_por_uf.png", dpi=200)
    plt.show()


def grafico_caps_vs_preco(df: pd.DataFrame):
    """
    Scatter: número de CAPS vs preço mediano, por UF.
    Tamanho do ponto proporcional ao número de profissionais.
    """
    data = df.dropna(subset=["caps_total", "preco_mediano"])

    plt.figure(figsize=(8, 6))
    sizes = (
        data["n_profissionais"] ** 0.5 * 10
    )  # ponto maior onde tem mais profissional

    plt.scatter(data["caps_total"], data["preco_mediano"], s=sizes)
    for _, row in data.iterrows():
        plt.text(
            row["caps_total"],
            row["preco_mediano"],
            row["UF"],
            fontsize=8,
            ha="center",
            va="bottom",
        )

    plt.title("Preço mediano vs número de CAPS por UF")
    plt.xlabel("Total de CAPS na UF")
    plt.ylabel("Preço mediano (R$)")
    plt.tight_layout()
    plt.savefig("graf_caps_vs_preco_mediano.png", dpi=200)
    plt.show()


def grafico_notif_vs_preco(df: pd.DataFrame):
    """
    Scatter: notificações de transtornos mentais (2020–2024) vs preço mediano
    """
    data = df.dropna(
        subset=["notificacoes_transtornos_mentais_2020_2024", "preco_mediano"]
    )

    plt.figure(figsize=(8, 6))
    plt.scatter(
        data["notificacoes_transtornos_mentais_2020_2024"],
        data["preco_mediano"],
    )

    for _, row in data.iterrows():
        plt.text(
            row["notificacoes_transtornos_mentais_2020_2024"],
            row["preco_mediano"],
            row["UF"],
            fontsize=8,
            ha="center",
            va="bottom",
        )

    plt.title("Preço mediano vs notificações de transtornos mentais (2020–2024)")
    plt.xlabel("Notificações de transtornos mentais (2020–2024)")
    plt.ylabel("Preço mediano (R$)")
    plt.tight_layout()
    plt.savefig("graf_notificacoes_vs_preco_mediano.png", dpi=200)
    plt.show()


def grafico_notif_por_prof_vs_preco(df: pd.DataFrame):
    """
    Scatter: notificações por profissional vs preço mediano
    """
    data = df.dropna(subset=["notificacoes_por_prof", "preco_mediano"])

    plt.figure(figsize=(8, 6))
    plt.scatter(
        data["notificacoes_por_prof"],
        data["preco_mediano"],
    )

    for _, row in data.iterrows():
        plt.text(
            row["notificacoes_por_prof"],
            row["preco_mediano"],
            row["UF"],
            fontsize=8,
            ha="center",
            va="bottom",
        )

    plt.title("Preço mediano vs notificações por profissional (2020–2024)")
    plt.xlabel("Notificações por profissional")
    plt.ylabel("Preço mediano (R$)")
    plt.tight_layout()
    plt.savefig("graf_notificacoes_por_prof_vs_preco_mediano.png", dpi=200)
    plt.show()


def main():
    df = load_summary()

    print("UFs na base:", sorted(df["UF"].unique()))
    print(
        df[
            [
                "UF",
                "n_profissionais",
                "preco_mediano",
                "caps_total",
                "notificacoes_transtornos_mentais_2020_2024",
            ]
        ]
    )

    grafico_preco_mediano_por_uf(df)
    grafico_caps_vs_preco(df)
    grafico_notif_vs_preco(df)
    grafico_notif_por_prof_vs_preco(df)


if __name__ == "__main__":
    main()
