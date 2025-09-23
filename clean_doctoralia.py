import pandas as pd
import re

# Carregar CSV gerado
df = pd.read_csv("doctoralia_psicologos_precos.csv")

# Manter só linhas que têm preço
df = df[df["preco_num"].notna()]

# Remover duplicatas pelo perfil_url
df = df.drop_duplicates(subset=["perfil_url"])


# Limpar coluna bairro_endereco (pegar só trechos que parecem endereço)
def clean_address(txt):
    if not isinstance(txt, str):
        return ""
    # regex para capturar "Rua ...", "Av. ...", ou cidade
    match = re.search(
        r"(Rua|Av\.?|Avenida|São Paulo|Rio de Janeiro|Belo Horizonte).*", txt
    )
    return match.group(0).strip() if match else txt.strip()


df["bairro_endereco"] = df["bairro_endereco"].apply(clean_address)

# Reordenar colunas
df = df[
    [
        "nome_anon",
        "cidade",
        "bairro_endereco",
        "servico",
        "preco_raw",
        "preco_num",
        "perfil_url",
    ]
]

# Salvar um novo CSV limpo
df.to_csv("doctoralia_psicologos_precos_limpo.csv", index=False, encoding="utf-8-sig")

print("Arquivo limpo salvo:", len(df), "linhas")
