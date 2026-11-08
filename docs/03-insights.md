# Relatório de insights

O recorte contém **96.203 pedidos da Olist** comprados de janeiro de 2017 a agosto de 2018 e entregues com datas válidas.

## O que encontramos

| Achado | Evidência | Implicação para a operação |
| --- | --- | --- |
| A pontualidade variou ao longo do tempo. | Foram 6.531 atrasos (6,79%). Entre os atrasados, o atraso mediano foi de 7 dias. O pico ocorreu em março de 2018, com 1.328 de 7.003 pedidos fora do prazo (18,96%). | Investigar o pico por rota e destino e acompanhar a taxa por mês da compra junto com o volume. |
| Taxa e volume indicam prioridades diferentes. | Entre as oito UFs com maior volume, BA e RJ tiveram taxas de 12,17% e 12,14%. SP teve uma taxa de 4,50% e o maior número de atrasos, com 1.817. | Priorizar RJ e BA ao investigar concentração de atrasos e incluir SP ao dimensionar o impacto em número de clientes. |
| O tipo de rota e a promessa merecem atenção. | Pedidos entre UFs atrasaram em 8,08% dos casos, ante 4,53% dentro da UF. A faixa prometida de até 7 dias teve 16,90% de atraso em 1.260 pedidos. | Revisar promessas curtas por destino e tipo de rota antes de alterar prazos. As diferenças podem refletir a composição dos pedidos. |
| Atraso e insatisfação aparecem juntos. | Entre os pedidos avaliados, 62,42% dos atrasados receberam nota 1 ou 2, ante 9,25% dos pedidos no prazo. Foram 6.378 e 89.182 avaliações nos respectivos grupos. | Testar se um aviso antecipado melhora a experiência dos clientes sinalizados. A comparação é observacional e se restringe a quem avaliou. |

Na EDA, as correlações de Spearman do atraso com frete, valor, quantidade de itens e dias prometidos foram fracas em nível individual (|ρ| ≤ 0,06). A faixa de até 7 dias, analisada separadamente, ilustra por que uma associação monotônica fraca pode coexistir com diferenças entre segmentos. A nota e o tempo realizado foram analisados apenas como resultados posteriores à compra.

## O que o modelo acrescenta

No teste de abril a agosto de 2018, houve 1.421 atrasos em 32.150 pedidos. A regressão logística obteve **precisão média (AP) de 8,01%**, ante **4,42%** da referência sem priorização. A ROC AUC foi de 0,652. O ganho permite concentrar mais atrasos na fila, com muitos alertas ainda dirigidos a pedidos que chegariam no prazo.

| Política no teste | Pedidos sinalizados | Atrasos capturados | Precisão dos alertas | Revocação dos atrasos |
| --- | ---: | ---: | ---: | ---: |
| Limiar fixado na validação | 7.689 (23,92%) | 588 | 7,65% | 41,38% |
| Cota de até 15% por dia | 4.744 (14,76%) | 431 | 9,09% | 30,33% |

A cota diária sinaliza os maiores scores do dia, arredondando a capacidade para baixo. No teste, a fila ficou aproximadamente **2,06 vezes** mais concentrada em atrasos do que a coorte de teste como um todo. O limiar fixo, calibrado para 15% na validação, sobrecarregaria a revisão no teste.

## Ações sugeridas

1. **Pilotar a fila com capacidade explícita.** Calcular o score na compra e revisar a fila ao fim do dia. Medir tempo gasto na revisão, taxa de alertas úteis, atrasos capturados e resultado das intervenções.
2. **Investigar os segmentos com taxa e volume relevantes.** Usar a tendência mensal e o recorte por destino para localizar os picos. Revisar a adequação dos prazos curtos por rota e volume.
3. **Medir o efeito do contato antecipado.** Comparar o piloto com um grupo de referência e acompanhar pontualidade e satisfação separadamente.

## Limitações

- O recorte é histórico e condicionado à entrega observada. Um piloto atual exigiria dados recentes e uma definição para pedidos cancelados, perdidos ou ainda em trânsito.
- O estudo usa a UF cadastrada do vendedor como aproximação da origem. A disponibilidade dos detalhes da cesta no checkout é uma premissa a confirmar com a operação.
- A data real de entrega foi exigida antes de cada corte de treino e validação. Isso preserva a cronologia e reduz a representação dos pedidos que demoraram mais a se resolver no fim dessas janelas. No teste, as métricas são retrospectivas.
- A cota foi simulada entre os pedidos entregues da coorte. A capacidade real e o custo de falsos alertas precisam ser medidos com todos os pedidos elegíveis para acompanhamento.
