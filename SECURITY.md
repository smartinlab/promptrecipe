# Security

## Reporting a vulnerability

Please report privately through GitHub's
[security advisories](https://github.com/smartinlab/promptrecipe/security/advisories/new)
rather than in a public issue. You can expect an acknowledgement within a
week.

## The threat model

The central assumption is that **fragment text is untrusted**. It may have
been written by a prompt optimizer, fetched from somewhere, or edited by
someone whose judgement you have not reviewed yet. The library is built so
that this does not matter:

- Fragment content is **never evaluated**. A fragment is inert text that may
  name a sibling with `[load namespace/path]` and nothing else. There is no
  expression language inside a fragment, so there is nothing to escape from.
  This is safety by construction rather than by sandbox — a deliberate
  choice, because sandboxes on general-purpose template engines have a long
  history of escapes, each fix followed by a new indirect route to the same
  primitive.
- **Caller-supplied values are substituted last and never re-parsed.** A
  value containing `[load ...]` or `{{...}}` appears verbatim in the output
  and loads nothing. The eval suite asserts this from outside the library.
- **Paths are confined to their namespace**, lexically and after symlink
  resolution. A fragment cannot reach outside the library root.
- **Recursion is bounded** — inclusion depth and expression depth both have
  ceilings, so a hostile or accidental cycle raises a typed error rather than
  exhausting the stack.
- **Every failure emits nothing.** There is no partial output to misread.

## What is out of scope

The library **produces** prompts. It never sends one to a model, and never
scores a result. Whatever your model does with an assembled prompt — prompt
injection through user-supplied values included — is your application's
concern, not this library's. What this library guarantees is that you can say
exactly which fragments produced the text you sent.

Access control is delegated to custody: filesystem permissions, and your
repository's permissions. The library holds no identity model and no
permission model.

## Supported versions

The latest tagged release. Fixes land on `main` and are tagged.
