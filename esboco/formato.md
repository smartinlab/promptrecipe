# Formato da receita — esboço

Uma receita é uma sequência de diretivas.

    [load <caminho>]        carrega um fragmento
    [if <condicao>] ...     carrega só se a condição valer

Caminho é hierárquico: `namespace/nome`. O namespace mapeia para uma pasta.

Variantes por modelo usam ponto: `core/tom.claude`, `core/tom.gpt`.
Assim dá para ter o prompt do Claude e o do GPT compartilhando os fragmentos
que não mudam, em vez de duas cópias que divergem.

## Em aberto

- Variável de valor (`{{cliente}}`) é a mesma coisa que variável que escolhe
  fragmento? Acho que não. Uma muda o conteúdo, a outra muda a estrutura.
- Ordem dos fragmentos importa. Declarar ou deixar implícito?
