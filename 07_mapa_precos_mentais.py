#!/usr/bin/env python3
"""
07_mapa_precos_mentais.py

Gera mapas simples (scatter) de municípios:
- cor = preço médio
- cor = casos F32/F41

Usa latitude/longitude do BR_Municipios_2023.csv.

Entrada:
- output/base_precos_mentais_2023.csv
- t_mentais_datasus-main/BR_Municipios_2023.csv

Saída:
- output/mapa_preco_psicologos.png
- output/mapa_casos_f32f41_psicologos.png
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_PATH = "output"
INPUT_BASE = os.path.join(BASE_PATH, "base_precos_mentais_2023.csv")
PATH_MUNICIPIOS = os.path.join("t_mentais_datasus-main", "BR_Municipios_2023.csv")


# ----------------------------------------------------------------------
# CARREGAR BASE INTEGRADA
# ----------------------------------------------------------------------
def carregar_base():
    if not os.path.exists(INPUT_BASE):
        raise FileNotFoundError(
            f"Arquivo {INPUT_BASE} não encontrado. Rode antes o 02_mentais_merge_exemplo.py."
        )
    df = pd.read_csv(INPUT_BASE, encoding="utf-8-sig")
    return df


# ----------------------------------------------------------------------
# CARREGAR MUNICÍPIOS (LAT / LONG)
# ----------------------------------------------------------------------
def carregar_municipios():
    if not os.path.exists(PATH_MUNICIPIOS):
        raise FileNotFoundError(f"Arquivo {PATH_MUNICIPIOS} não encontrado.")

    # 1ª tentativa: separador ';'
    df = pd.read_csv(PATH_MUNICIPIOS, sep=";")
    print("Colunas BR_Municipios_2023 (1ª leitura):", list(df.columns))

    # Se veio uma coluna só tipo "codigo_ibge,nome,..." é porque o separador não era ';'
    if len(df.columns) == 1 and "codigo_ibge" not in df.columns:
        df = pd.read_csv(PATH_MUNICIPIOS)  # tenta com separador padrão ','
        print("Colunas BR_Municipios_2023 (2ª leitura):", list(df.columns))

    # Agora renomeia se tiver os nomes "originais" do IBGE
    if "codigo_ibge" in df.columns:
        df = df.rename(
            columns={
                "codigo_ibge": "CD_MUN",
                "nome": "NM_MUN",
                "codigo_uf": "CD_UF",
            }
        )

    # Segurança: conferir se CD_MUN existe agora
    if "CD_MUN" not in df.columns:
        raise KeyError(
            "Não encontrei a coluna 'CD_MUN' nem 'codigo_ibge' em BR_Municipios_2023.csv. "
            "Confira o cabeçalho do arquivo."
        )

    # Garante que o código IBGE tem 7 dígitos
    df["CD_MUN"] = df["CD_MUN"].astype(str).str.zfill(7)

    return df


# ----------------------------------------------------------------------
# JUNTAR LAT/LONG NA BASE
# ----------------------------------------------------------------------
def anexar_lat_long(base, municipios):
    base = base.copy()
    municipios = municipios[["CD_MUN", "latitude", "longitude"]].copy()
    base = base.merge(municipios, left_on="cod_mun_ibge", right_on="CD_MUN", how="left")
    return base


# ----------------------------------------------------------------------
# PLOT SIMPLES DE SCATTER
# ----------------------------------------------------------------------
def plot_scatter_mapa(df, valor_col, titulo, arquivo_saida):
    sub = df.dropna(subset=["latitude", "longitude", valor_col]).copy()
    if sub.empty:
        print(f"⚠️ Sem dados suficientes para {titulo}")
        return

    plt.figure(figsize=(8, 8))
    sc = plt.scatter(
        sub["longitude"],
        sub["latitude"],
        c=sub[valor_col],
        s=40,
        alpha=0.8,
    )
    plt.colorbar(sc, label=valor_col)
    plt.title(titulo)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()

    os.makedirs(BASE_PATH, exist_ok=True)
    out_path = os.path.join(BASE_PATH, arquivo_saida)
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ Mapa salvo em {out_path}")


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def main():
    base = carregar_base()
    municipios = carregar_municipios()
    base = anexar_lat_long(base, municipios)

    # exemplo: psicólogos
    base_psic = base[base["tipo_profissional"] == "psicologo"].copy()
    base_psic["casos_f32_f41"] = base_psic["casos_f32_f41"].fillna(0)

    # mapa de preços
    plot_scatter_mapa(
        base_psic,
        "preco_medio",
        "Preço médio de psicólogos por município (2023)",
        "mapa_preco_psicologos.png",
    )

    # mapa de casos F32/F41
    plot_scatter_mapa(
        base_psic,
        "casos_f32_f41",
        "Casos F32/F41 por município (2023)",
        "mapa_casos_f32f41_psicologos.png",
    )


if __name__ == "__main__":
    main()
