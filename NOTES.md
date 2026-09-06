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

- Fragmento endereçado por caminho, uma pasta por namespace, um arquivo por
  fragmento. Isso funcionou.
- Variante por ponto (`tom.claude`). Também funcionou.
- Receita como lista de `[load]` com condição.

O que muda:

- **Motor próprio, não emprestado.** A gramática precisa ser pequena o
  bastante para eu conseguir dizer o que ela NÃO faz. Conteúdo de fragmento
  nunca é avaliado.
- **Identidade em toda montagem.** Se não dá para dizer o que gerou um
  resultado, o resto não importa.
- **Colisão é erro, não escolha.** Nunca escolher em silêncio.
- Separar variável que muda estrutura de variável que muda conteúdo. São
  coisas diferentes e eu estava tratando como a mesma.

Antes de escrever código dessa vez: pesquisar o que já existe e escrever
o que estou construindo.

---

## 2026-09-05 — custódia versionada não vai existir

Ia construir um adaptador de custódia versionada (T-025). Não vou.

O fragmento mora no repositório do projeto que consome a lib. Então o git
*daquele* projeto já versiona o fragmento. `FsCustody` lê a working tree, e
como um fragmento é um arquivo (ADR-007), `git log`, `git blame` e review de
PR já funcionam por fragmento. Não falta nada.

Construir o adaptador seria reimplementar o que o repositório hospedeiro faz
melhor — que é exatamente o que o amendment 7 delegou pra fora. Teria sido a
delegação voltando atrás em silêncio, com um nome de tarefa em cima.

`FsCustody.versions()` devolver exatamente uma identidade deixa de ser
provisório e passa a ser a resposta. Histórico é `git log`, não é atribuição
desta lib.

**O custo, que fica anotado:** isso deixa a T-026 (custódia remota) mais
travada, não menos. Antes eu podia dizer "a custódia versionada é
pré-requisito do review". Agora a única fonte de review é o repositório do
projeto — então tirar o fragmento de lá não perde uma opção entre duas, perde
o review inteiro. A pergunta de produto continua aberta e ficou mais afiada.

E sem custódia remota também, por ora.

Isso não é só menos escopo — fecha o único buraco que o TRD tinha anotado. A
delegação do review pro version control (ADR-007) valia *enquanto* o fragmento
estivesse versionado; o TRD registrou duas saídas possíveis pro caso remoto e
não escolheu nenhuma. Agora não precisa escolher: não existe o caso. Custódia
é o repositório do projeto, e só ele.

Resolver removendo o caso é melhor do que resolver remendando. A pergunta que
sobra fica anotada pra quem um dia reviver o remoto: é *distribuição* de uma
biblioteca já revisada (read-only, o buraco continua fechado) ou é *edição*
fora do repositório (aí perde o review inteiro)? São coisas diferentes e a
segunda obrigaria a construir o que o amendment 7 mandou não construir.

`Custody.versions()` fica no port, mas agora é uma costura reservada, não uma
promessa. Nenhum backend atual tem mais de uma resposta.
