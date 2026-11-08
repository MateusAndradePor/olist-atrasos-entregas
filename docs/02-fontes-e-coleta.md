# Fontes e coleta de dados

O projeto usa o **Brazilian E-Commerce Public Dataset by Olist**, versão 2, publicado pela Olist no Kaggle. São dados estruturados, públicos e anonimizados, em arquivos CSV. A página da base indica a licença **CC BY-NC-SA 4.0**. [Catálogo e licença indicados pela Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

| CSV usado | Unidade | Linhas na origem | Uso |
| --- | --- | ---: | --- |
| `olist_orders_dataset.csv` | Pedido | 99.441 | Status, data da compra, data prometida e data da entrega. |
| `olist_customers_dataset.csv` | Registro de cliente associado ao pedido | 99.441 | UF do destino, por `customer_id`. |
| `olist_order_items_dataset.csv` | Item de pedido | 112.650 | Quantidades, vendedores, valores e frete, agregados por `order_id`. |
| `olist_sellers_dataset.csv` | Vendedor | 3.095 | UF do cadastro do vendedor, por `seller_id`. |
| `olist_order_reviews_dataset.csv` | Registro de avaliação | 99.224 | Nota de satisfação, apenas para análise exploratória. |

## Método de acesso

O ZIP foi obtido diretamente pelo endpoint de download do Kaggle, com a versão indicada na URL. O script lê os cinco CSVs de dentro do ZIP. Os arquivos de geolocalização, pagamentos, produtos e traduções ficaram fora do recorte.

```powershell
New-Item -ItemType Directory -Force data/raw | Out-Null
curl.exe --fail --location "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce?datasetVersionNumber=2" --output data/raw/olist-v2.zip
```

Também é possível baixar a versão 2 pela página do conjunto no Kaggle e salvar o arquivo em `data/raw/olist-v2.zip`. O ZIP usado nesta análise tem 44.717.580 bytes e SHA-256 `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`.

## Tratamento e publicação

As junções têm cardinalidade verificada. Os itens são consolidados antes da junção com pedidos para preservar uma linha por compra. Entre avaliações com nota válida, fica a resposta mais recente por pedido. Comentários, nomes de cidades e CEPs ficam fora da leitura. Os identificadores originais servem apenas para cruzar as tabelas localmente.

O repositório exclui o ZIP bruto. O CSV do painel reúne contagens e somas por mês da compra, UF do cliente, tipo de rota, faixa do prazo prometido e situação da entrega, com crédito à Olist. A licença da fonte é indicada para os dados derivados.
