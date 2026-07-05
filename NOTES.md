# Notas

## 2026-05-16

Primeira abordagem: usar um motor de template pronto (Jinja) e tratar cada
fragmento como um sub-template incluído via `{% include %}`.

Parece o caminho óbvio. O motor já resolve variáveis, condicionais e inclusão.

Coisas que ainda não sei responder:

- Como saber qual fragmento gerou qual pedaço do prompt final?
- Se dois lugares definem `core/tom`, qual ganha?
- Como reproduzir exatamente o prompt que gerou um resultado de ontem?

## 2026-07-05

O motor de template pronto não serve, e o motivo não é performance.

**Fragmento vira template.** O `{% include %}` renderiza o conteúdo incluído.
Ou seja: o texto do fragmento é executado. Isso passa a importar muito no dia
em que um otimizador escrever o fragmento — aí é entrada não confiável sendo
avaliada.

**Sem identidade.** Não consigo dizer "este resultado veio deste prompt".
Cada montagem é uma string nova e pronto. Sem isso, comparar duas versões
não significa nada.

**Colisão silenciosa.** Dois lugares definindo o mesmo nome: o motor escolhe
um e segue. Nenhum erro. Foi assim que perdi uma tarde.

Acho que o erro foi partir da ferramenta em vez de partir do problema.
O problema não é montar texto — montar texto é fácil. O problema é saber
o que foi montado.

## 2026-08-23

Decidi recomeçar do zero em vez de remendar.

O que fica:
