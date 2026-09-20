# OcéEns

EPF's teaching evaluation platform: surveys are created per program, students answer them,
and the answers are exported, visualised and summarised.

## Language boundary

The documentation, the code identifiers and the issues are in **English**. The **product**
is in French: the rendered pages, the survey questions, the seeded demo content and the
messages shown to a user stay in French, as do the code comments and log messages already
written in it. Quote a French label as-is rather than translating it in passing — a
translated label no longer matches what is on screen.

The code already names the domain in English; these are the same things under two names:

| In the product (French) | In the code and the docs (English) |
|---|---|
| sondage | survey (`Survey`) |
| synthèse | summary (`Summary`) |
| filière | program (`Program`, role scope) |
| animateur | facilitator |
| direction de campus | campus manager |
| responsable de programme | program manager |
| enseignant | teacher |
| verbatim | verbatim (unchanged) |

## Vocabulary

### Authentication

**Dev sign-in** (`AUTH_MODE=dev`):
Sign-in with no identity provider: you pick a user's mail address and are signed in as
them, with no proof of identity. It exists only when `AUTH_MODE=dev` and must never be
used in production.
_Avoid_: impersonation, spoofing, fake login
