# promptrecipe

Prompts são tratados como string. Deveriam ser tratados como código.

A ideia: um **template** (receita) com variáveis, onde as variáveis são
preenchidas por **fragmentos** — pedaços de prompt reutilizáveis, endereçados
por caminho. Combinando fragmentos você monta o prompt final.

```
[load core/identidade]
[load core/tom]
[load core/seguranca]
```

Se a mesma instrução aparece em trinta prompts, ela deveria ser um fragmento
só. Hoje é copiar e colar — e quando está errada, você tem que achar as trinta.

## Por quê

Comecei com seis prompts. Agora tenho dezenas, e não confio mais que estejam
consistentes. Sei que tem instrução errada em produção porque consertar
significa achar todas as cópias.

## Status

Ideia. Nada implementado ainda.
