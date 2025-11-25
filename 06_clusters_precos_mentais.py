#!/usr/bin/env python3
"""
06_clusters_precos_mentais.py

Clusterização de municípios usando:
- preco_medio
- casos_f32_f41
- qtd_profissionais

Separado para psicólogos e psiquiatras (clusters por tipo de profissional).

Entrada: output/base_precos_mentais_2023.csv
Saída:
- output/base_precos_mentais_2023_clusters.csv
- estatísticas de cada cluster no terminal
"""

import os
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

BASE_PATH = "output"
INPUT_FILE = os.path.join(BASE_PATH, "base_precos_mentais_2023.csv")
OUTPUT_FILE = os.path.join(BASE_PATH, "base_precos_mentais_2023_clusters.csv")


def carregar_base():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_FILE}. Rode antes o 02_mentais_merge_exemplo.py"
        )
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    return df


def preparar_dados(df):
    for col in ["preco_medio", "qtd_profissionais", "casos_f32_f41"]:
        if col not in df.columns:
            df[col] = 0.0

    df["preco_medio"] = pd.to_numeric(df["preco_medio"], errors="coerce")
    df["qtd_profissionais"] = pd.to_numeric(df["qtd_profissionais"], errors="coerce")
    df["casos_f32_f41"] = pd.to_numeric(df["casos_f32_f41"], errors="coerce").fillna(0)

    return df


def clusterizar_tipo(df, tipo, k=3):
    sub = df[df["tipo_profissional"] == tipo].copy()
    if sub.empty:
        print(f"\n⚠️ Sem dados para {tipo}")
        return df

    features = ["preco_medio", "casos_f32_f41", "qtd_profissionais"]
    X = sub[features].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    col_cluster = f"cluster_{tipo}"
    df.loc[sub.index, col_cluster] = clusters

    print(f"\n=== Clusters para {tipo.upper()} (k={k}) ===")
    resumo = (
        df.loc[sub.index, ["cidade_oficial", "uf_oficial", col_cluster] + features]
        .groupby(col_cluster)
        .agg(
            {
                "preco_medio": "mean",
                "casos_f32_f41": "mean",
                "qtd_profissionais": "mean",
            }
        )
        .round(2)
    )
    print(resumo)

    return df


def main():
    df = carregar_base()
    df = preparar_dados(df)

    for tipo in ["psicologo", "psiquiatra"]:
        df = clusterizar_tipo(df, tipo, k=3)

    os.makedirs(BASE_PATH, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ Base com clusters salva em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
