# Prever atrasos nas entregas do e-commerce

Uma compra online cria um compromisso concreto com o cliente: entregar o pedido até a data informada. Se a operação acompanha todos os pedidos da mesma forma, os casos que exigem atenção podem passar despercebidos até a data limite. Também é inviável dedicar a mesma revisão manual a cada compra quando a equipe tem capacidade limitada.

Neste projeto, a equipe de logística é quem toma a decisão. A pergunta é **quais pedidos merecem acompanhamento prioritário já no momento da compra?** A aplicação proposta é uma fila de revisão antecipada. Ao receber um alerta, a equipe pode confirmar o andamento do pedido, investigar a rota e avaliar quando comunicar o cliente.

## Por que usar dados

As datas prometida e realizada permitem medir a proporção de pedidos entregues após o prazo e quantos dias de atraso ocorreram. O histórico também permite investigar como essa proporção varia ao longo do tempo, entre destinos e tipos de rota, e entre faixas de prazo prometido.

Na modelagem, podemos testar se sinais disponíveis na compra ajudam a ordenar pedidos por prioridade. A avaliação em meses posteriores mede quantos atrasos a fila teria capturado e quantos pedidos teria encaminhado desnecessariamente. Esses dois números importam para uma operação com capacidade limitada.

## Escopo

- **Unidade de análise** · Um pedido, ainda que reúna vários itens ou vendedores.
- **Recorte** · Compras da Olist feitas de janeiro de 2017 a agosto de 2018, com entrega registrada e campos mínimos válidos.
- **Atraso** · Data de entrega posterior à data prometida, em dias corridos. Entrega em qualquer horário da data prometida conta como dentro do prazo.
- **Decisão** · Selecionar pedidos para revisão humana. O benefício de uma intervenção teria de ser medido em um piloto.

O histórico permite avaliar a pontualidade entre pedidos entregues. Cancelamentos e pedidos sem desfecho de entrega requerem uma definição própria para serem incorporados à fila. Os dados representam a operação observada no período e precisariam ser atualizados antes de uma aplicação atual.
