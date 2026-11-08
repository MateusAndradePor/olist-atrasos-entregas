"""Análise reproduzível de entregas da Olist, com uma observação por pedido."""

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
ARQUIVO = ROOT / "data" / "raw" / "olist-v2.zip"
INICIO = pd.Timestamp("2017-01-01")
INICIO_VALIDACAO = pd.Timestamp("2018-01-01")
INICIO_TESTE = pd.Timestamp("2018-04-01")
FIM = pd.Timestamp("2018-09-01")
ORCAMENTO_ALERTAS = 0.15

FAIXAS_PRAZO = ["Até 7 dias", "8 a 14 dias", "15 a 21 dias", "22 a 30 dias", "31+ dias"]
NUMERICAS = ["log_itens", "log_vendedores", "log_valor", "log_frete"]
CATEGORICAS = ["uf_destino", "rota", "faixa_prazo", "dia_semana", "turno"]


def preparar_pedidos(arquivo=ARQUIVO):
    """Carrega os CSVs originais, valida as junções e constrói a coorte."""
    with ZipFile(arquivo) as zip_base:
        with zip_base.open("olist_orders_dataset.csv") as csv:
            pedidos = pd.read_csv(csv, usecols=[
                "order_id", "customer_id", "order_status", "order_purchase_timestamp",
                "order_delivered_customer_date", "order_estimated_delivery_date",
            ]).rename(columns={
                "order_purchase_timestamp": "compra",
                "order_delivered_customer_date": "entrega",
                "order_estimated_delivery_date": "promessa",
            })
        with zip_base.open("olist_customers_dataset.csv") as csv:
            clientes = pd.read_csv(csv, usecols=["customer_id", "customer_state"])
        with zip_base.open("olist_order_items_dataset.csv") as csv:
            itens = pd.read_csv(csv, usecols=[
                "order_id", "order_item_id", "seller_id", "price", "freight_value",
            ])
        with zip_base.open("olist_sellers_dataset.csv") as csv:
            vendedores = pd.read_csv(csv, usecols=["seller_id", "seller_state"])
        with zip_base.open("olist_order_reviews_dataset.csv") as csv:
            avaliacoes = pd.read_csv(csv, usecols=[
                "order_id", "review_id", "review_score", "review_answer_timestamp",
            ])

    if pedidos.order_id.duplicated().any() or itens.duplicated(["order_id", "order_item_id"]).any():
        raise ValueError("Chaves duplicadas nos pedidos ou nos itens.")
    if itens[["price", "freight_value"]].isna().any().any() or (itens[["price", "freight_value"]] < 0).any().any():
        raise ValueError("Itens com preço ou frete ausente ou negativo.")

    for coluna in ["compra", "entrega", "promessa"]:
        pedidos[coluna] = pd.to_datetime(pedidos[coluna], errors="coerce")
    n_fonte = len(pedidos)
    pedidos = pedidos.loc[pedidos.compra.ge(INICIO) & pedidos.compra.lt(FIM)].copy()
    n_periodo = len(pedidos)
    status = pedidos.order_status.value_counts().rename_axis("status").rename("pedidos")
    pedidos = pedidos.loc[pedidos.order_status.eq("delivered")].copy()
    n_entregues = len(pedidos)
    datas_validas = pedidos[["entrega", "promessa"]].notna().all(axis=1)
    datas_validas &= pedidos.entrega.ge(pedidos.compra)
    datas_validas &= pedidos.promessa.dt.normalize().ge(pedidos.compra.dt.normalize())
    pedidos = pedidos.loc[datas_validas].copy()

    pedidos = pedidos.merge(clientes, on="customer_id", how="left", validate="many_to_one")
    pedidos = pedidos.rename(columns={"customer_state": "uf_destino"})
    itens = itens.merge(vendedores, on="seller_id", how="left", validate="many_to_one")
    itens = itens.merge(pedidos[["order_id", "uf_destino"]], on="order_id", validate="many_to_one")
    itens["origem_conhecida"] = itens.seller_state.notna()
    itens["mesma_uf"] = itens.seller_state.eq(itens.uf_destino)
    cesta = itens.groupby("order_id", sort=False).agg(
        n_itens=("order_item_id", "size"),
        n_vendedores=("seller_id", "nunique"),
        valor=("price", "sum"),
        frete=("freight_value", "sum"),
        origens_conhecidas=("origem_conhecida", "sum"),
        itens_mesma_uf=("mesma_uf", "sum"),
    )
    pedidos = pedidos.merge(cesta, on="order_id", how="left", validate="one_to_one")
    tem_cesta_e_uf = pedidos.n_itens.notna() & pedidos.uf_destino.notna()
    tem_cesta_e_uf &= pedidos.origens_conhecidas.eq(pedidos.n_itens)
    pedidos = pedidos.loc[tem_cesta_e_uf].copy()
    pedidos["rota"] = np.select(
        [pedidos.itens_mesma_uf.eq(pedidos.n_itens), pedidos.itens_mesma_uf.eq(0)],
        ["Dentro da UF", "Entre UFs"],
        default="Mista",
    )

    # A nota é usada apenas na EDA. A pesquisa pode ter várias respostas por pedido.
    avaliacoes = avaliacoes.loc[avaliacoes.review_score.between(1, 5)]
    avaliacoes = avaliacoes.sort_values(["review_answer_timestamp", "review_id"])
    avaliacoes = avaliacoes.drop_duplicates("order_id", keep="last")
    pedidos = pedidos.merge(
        avaliacoes[["order_id", "review_score"]], on="order_id", how="left", validate="one_to_one",
    ).rename(columns={"review_score": "nota"})

    pedidos["dias_diferenca"] = (pedidos.entrega.dt.normalize() - pedidos.promessa.dt.normalize()).dt.days
    pedidos["atrasou"] = pedidos.dias_diferenca.gt(0)
    pedidos["dias_atraso"] = pedidos.dias_diferenca.clip(lower=0)
    pedidos["dias_prometidos"] = (pedidos.promessa.dt.normalize() - pedidos.compra.dt.normalize()).dt.days
    pedidos["dias_ate_entrega"] = (pedidos.entrega.dt.normalize() - pedidos.compra.dt.normalize()).dt.days
    pedidos["faixa_prazo"] = pd.cut(
        pedidos.dias_prometidos, bins=[-1, 7, 14, 21, 30, np.inf], labels=FAIXAS_PRAZO,
    )
    pedidos["dia_semana"] = pedidos.compra.dt.dayofweek.astype(str)
    pedidos["turno"] = pd.cut(
        pedidos.compra.dt.hour, bins=[-1, 5, 11, 17, 23],
        labels=["Madrugada", "Manhã", "Tarde", "Noite"],
    )
    pedidos["mes_compra"] = pedidos.compra.dt.to_period("M").dt.to_timestamp()
    for campo in ["n_itens", "n_vendedores", "valor", "frete"]:
        pedidos[f"log_{campo.removeprefix('n_')}"] = np.log1p(pedidos[campo])

    auditoria = pd.Series({
        "Pedidos no arquivo": n_fonte,
        "Pedidos dentro do recorte": n_periodo,
        "Pedidos com status entregue": n_entregues,
        "Entregues excluídos por datas ausentes ou incoerentes": n_entregues - int(datas_validas.sum()),
        "Excluídos por falta de itens ou UF": int((~tem_cesta_e_uf).sum()),
        "Pedidos na coorte": len(pedidos),
        "Pedidos com nota": int(pedidos.nota.notna().sum()),
    }, name="pedidos")
    return pedidos, auditoria, status


def resumo_por(pedidos, dimensao):
    resumo = pedidos.groupby(dimensao, observed=True).agg(
        pedidos=("atrasou", "size"), atrasados=("atrasou", "sum"),
        dias_ate_entrega_mediana=("dias_ate_entrega", "median"),
    )
    resumo["taxa_atraso"] = resumo.atrasados / resumo.pedidos
    return resumo


def avaliar_modelo(pedidos):
    """Treina no passado, fixa o limiar na validação e mede o teste futuro."""
    treino = pedidos.loc[pedidos.compra.lt(INICIO_VALIDACAO) & pedidos.entrega.lt(INICIO_VALIDACAO)]
    validacao = pedidos.loc[
        pedidos.compra.ge(INICIO_VALIDACAO) & pedidos.compra.lt(INICIO_TESTE) & pedidos.entrega.lt(INICIO_TESTE)
    ]
    teste = pedidos.loc[pedidos.compra.ge(INICIO_TESTE)].copy()
    colunas = NUMERICAS + CATEGORICAS
    pre_processamento = ColumnTransformer([
        ("numericas", StandardScaler(), NUMERICAS),
        ("categoricas", OneHotEncoder(handle_unknown="ignore", min_frequency=30), CATEGORICAS),
    ])
    modelo = make_pipeline(pre_processamento, LogisticRegression(max_iter=1000))
    modelo.fit(treino[colunas], treino.atrasou)
    score_validacao = modelo.predict_proba(validacao[colunas])[:, 1]
    limiar = float(np.quantile(score_validacao, 1 - ORCAMENTO_ALERTAS, method="higher"))
    teste["score"] = modelo.predict_proba(teste[colunas])[:, 1]
    alerta_limiar = teste.score.gt(limiar)

    # Os scores são calculados na compra. A equipe revisa uma fila ao fim do dia.
    teste = teste.sort_values(["compra", "order_id"])
    taxa_uf_treino = treino.groupby("uf_destino").atrasou.mean()
    teste["score_uf"] = teste.uf_destino.map(taxa_uf_treino).fillna(treino.atrasou.mean())
    por_dia = teste.groupby(teste.compra.dt.normalize())
    cota_diaria = np.floor(ORCAMENTO_ALERTAS * por_dia["score"].transform("size"))
    posicoes = por_dia[["score", "score_uf"]].rank(method="first", ascending=False)
    teste["alerta"] = posicoes.score.le(cota_diaria)
    alerta_referencia_uf = posicoes.score_uf.le(cota_diaria)
    teste["detectado"] = teste.alerta & teste.atrasou

    metricas = pd.DataFrame([
        medir(validacao.atrasou, score_validacao, score_validacao > limiar),
        medir(teste.atrasou, teste.score, alerta_limiar.reindex(teste.index)),
        medir(teste.atrasou, teste.score, teste.alerta),
        medir(teste.atrasou, teste.score_uf, alerta_referencia_uf),
    ], index=["Validação · limiar", "Teste · limiar", "Teste · cota diária", "Teste · regra por UF"])
    particoes = pd.DataFrame([
        {"particao": nome, "pedidos": len(parte), "atrasados": int(parte.atrasou.sum())}
        for nome, parte in [("Treino", treino), ("Validação", validacao), ("Teste", teste)]
    ]).set_index("particao")
    return teste, metricas, particoes, limiar


def medir(atrasou, score, alerta):
    detectados = int((atrasou & alerta).sum())
    alertas = int(alerta.sum())
    atrasos = int(atrasou.sum())
    prevalencia = float(atrasou.mean())
    precisao = detectados / alertas if alertas else 0.0
    return {
        "pedidos": len(atrasou), "atrasos": atrasos, "taxa_atraso": prevalencia,
        "ap_referencia_aleatoria": prevalencia,
        "ap_score": average_precision_score(atrasou, score),
        "roc_auc": roc_auc_score(atrasou, score),
        "alertas": alertas, "atrasos_detectados": detectados,
        "percentual_alertado": alertas / len(atrasou),
        "precisao": precisao, "revocacao": detectados / atrasos,
        "lift": precisao / prevalencia,
    }


def exportar_painel(pedidos, teste, destino):
    """Exporta somas agregáveis para filtros no Looker Studio."""
    dimensoes = ["mes_compra", "uf_destino", "rota", "faixa_prazo", "situacao"]
    painel = pedidos.merge(teste[["order_id", "alerta", "detectado"]], on="order_id", how="left", validate="one_to_one")
    painel["situacao"] = np.where(painel.atrasou, "Atrasado", "No prazo")
    painel["no_teste"] = painel.alerta.notna()
    painel["atraso_teste"] = painel.no_teste & painel.atrasou
    painel["alerta"] = painel.alerta.eq(True)
    painel["detectado"] = painel.detectado.eq(True)
    painel["avaliado"] = painel.nota.notna()
    painel["nota_baixa"] = painel.nota.le(2)
    agregado = painel.groupby(dimensoes, observed=True).agg(
        pedidos=("atrasou", "size"), atrasados=("atrasou", "sum"),
        soma_dias_atraso=("dias_atraso", "sum"), avaliacoes=("avaliado", "sum"),
        notas_baixas=("nota_baixa", "sum"), soma_notas=("nota", "sum"),
        pedidos_teste=("no_teste", "sum"), atrasos_teste=("atraso_teste", "sum"),
        alertas=("alerta", "sum"), atrasos_detectados=("detectado", "sum"),
    ).reset_index()
    destino.parent.mkdir(parents=True, exist_ok=True)
    agregado.to_csv(destino, index=False, date_format="%Y-%m-%d")
    return agregado


if __name__ == "__main__":
    coorte, auditoria, _ = preparar_pedidos()
    teste, metricas, particoes, limiar = avaliar_modelo(coorte)
    exportar_painel(coorte, teste, ROOT / "dashboard" / "dados_painel.csv")
    print(auditoria.to_string(), "\n\n", particoes.to_string(), sep="")
    print(f"\nLimiar fixado na validação: {limiar:.4f}\n")
    print(metricas.T.to_string(float_format=lambda x: f"{x:.4f}"))
