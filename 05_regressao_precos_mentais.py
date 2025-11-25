#!/usr/bin/env python3
"""
05_regressao_precos_mentais.py

Regressão linear simples:
  preco_medio ~ casos_f32_f41

Focado em psicólogos (tipo_profissional == "psicologo").

Usa:
  output/base_precos_mentais_2023.csv
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
import numpy as np

BASE_PATH = "output"
INPUT_BASE = os.path.join(BASE_PATH, "base_precos_mentais_2023.csv")


def carregar_base():
    if not os.path.exists(INPUT_BASE):
        raise FileNotFoundError(
            f"Arquivo {INPUT_BASE} não encontrado. "
            "Certifique-se de ter rodado antes o 02_mentais_merge_exemplo.py."
        )
    df = pd.read_csv(INPUT_BASE, encoding="utf-8-sig")
    return df


def regressao_psicologos(df):
    sub = df[df["tipo_profissional"] == "psicologo"].copy()
    sub = sub.dropna(subset=["preco_medio"])
    sub["casos_f32_f41"] = sub["casos_f32_f41"].fillna(0)

    if sub.empty:
        print("⚠️ Nenhum dado de psicólogo para regressão.")
        return

    X = sub[["casos_f32_f41"]].values
    y = sub["preco_medio"].values

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)

    r2 = r2_score(y, y_pred)
    mae = mean_absolute_error(y, y_pred)

    print("=== Regressão linear – Psicólogos ===")
    print("Coeficiente (beta casos_f32_f41):", float(model.coef_[0]))
    print("Intercepto:", float(model.intercept_))
    print("R²:", r2)
    print("MAE:", mae)

    # Gráfico: pontos + linha
    x_sorted = np.sort(X[:, 0])
    y_line = model.predict(x_sorted.reshape(-1, 1))

    plt.figure(figsize=(7, 5))
    plt.scatter(X[:, 0], y)
    plt.plot(x_sorted, y_line)
    plt.title("Regressão: preço médio x casos F32/F41 (psicólogos)")
    plt.xlabel("Casos F32/F41 (2023)")
    plt.ylabel("Preço médio da sessão (R$)")
    plt.tight_layout()

    os.makedirs(BASE_PATH, exist_ok=True)
    out = os.path.join(BASE_PATH, "regressao_preco_vs_casos_psicologos.png")
    plt.savefig(out, dpi=300)
    print(f"✅ Gráfico de regressão salvo em {out}")

    plt.show()


def main():
    df = carregar_base()
    regressao_psicologos(df)


if __name__ == "__main__":
    main()
