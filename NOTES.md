# Notas

## 2026-05-16

Primeira abordagem: usar um motor de template pronto (Jinja) e tratar cada
fragmento como um sub-template incluído via `{% include %}`.

Parece o caminho óbvio. O motor já resolve variáveis, condicionais e inclusão.

Coisas que ainda não sei responder:

- Como saber qual fragmento gerou qual pedaço do prompt final?
- Se dois lugares definem `core/tom`, qual ganha?
- Como reproduzir exatamente o prompt que gerou um resultado de ontem?
