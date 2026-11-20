# Tradition vocabulary

Later church words that the Hebrew/Aramaic/Greek text never literally says. **On `Literal:` and `Natural:` lines these terms are errors** (`check_sermon.py`, case-insensitive whole-word match on the `term` column). In prose and Notes they may be named and discussed — e.g. "the word many Bibles render *church* is ἐκκλησία, an assembly".

Rules for this table:

- `term` is the only machine-read column. One word form per row (matching is whole-word, so inflections need their own rows), or a stem ending in `*`, which matches every word that starts with it (`bautiz*` = bautizo, bautizad, bautizarlos …). Use a stem only when every word it can match is the tradition term — never a stem that also starts ordinary words.
- A term belongs here only if its plain rendering is defensible from the original word. Capitalization-only issues (*Holy Spirit* vs *holy spirit*, *Espíritu Santo* vs *espíritu santo*, *Hijo*, *Verbo*-as-title) cannot be matched case-insensitively and live in `fidelity-rules.md` instead.
- Words that are ordinary plain renderings in the target language stay out even if churches also use them (es *santo* = "holy", *pastor* = "shepherd", *Pascua* = Passover in Spanish), *gentiles* = also the plural of *gentil* "kind", *comforter/consolador* = plain in the OT, e.g. Eccl.4.1, Lam.1.16). Standard lexical equivalents stay out too: *repent/arrepentirse* is the ordinary rendering of μετανοέω — show its range from usage when it matters (`fidelity-rules.md` §2), don't ban it.
- Counts and LXX notes below come from `lookup.py word`/`usage` output; LXX figures are same-verse co-occurrence, not alignment.

| lang | term | plain rendering | note |
|---|---|---|---|
| en | church | assembly, gathering | ἐκκλησία; NT 114 (SBL; TR 116), LXX 77 (co-occurs with קָהָל 66×); also a civic assembly (Acts.19.32) |
| en | churches | assemblies | plural of the above |
| en | baptize | immerse, dip, wash — say which the context shows | βαπτίζω; LXX 2Kgs.5.14 Naaman in the Jordan; Luke.11.38 and Mark.7.4 of washing before meals; Josephus of sinking ships. Don't assert a mode the verse doesn't show |
| en | baptized | immersed, dipped, washed | inflection |
| en | baptizing | immersing, washing | inflection |
| en | baptizes | immerses, washes | inflection |
| en | baptise | immerse, wash | British spelling |
| en | baptised | immersed, washed | British spelling |
| en | baptizer | immerser, washer | ὁ βαπτίζων (Mark.6.14) |
| en | baptism | immersion, washing | βάπτισμα; related βαπτισμός "washing" (Mark.7.4 βαπτισμοὺς ποτηρίων, Heb.6.2) |
| en | baptisms | immersions, washings | Heb.6.2 βαπτισμῶν (βαπτισμός) |
| en | baptist | immerser, washer | ὁ βαπτιστής (John) |
| en | baptiz* | immerse, wash (any form) | stem: every baptiz- word (baptizing, baptizeth …) |
| en | baptis* | immerse, immersion, wash (any form) | stem: baptism, baptismal, baptist, baptise … |
| en | evangeli* | good news, announce good news | stem: evangelize, evangelism, evangelical … (εὐαγγελ-) |
| en | holy ghost | holy spirit (lower case), holy breath | πνεῦμα ἅγιον / רוּחַ; capitals: see fidelity-rules.md |
| en | godhead | deity, divine nature | KJV for θεότης (Col.2.9, NT 1×) and related words |
| en | trinity | — (no word in the text) | describe what the verse itself says |
| en | triune | — | same |
| en | sacrament | — | Latin *sacramentum*; the Greek nearby is usually μυστήριον "secret, mystery" |
| en | rapture | caught up, snatched away | ἁρπάζω (1Thess.4.17); Latin *rapere* |
| en | eucharist | thanksgiving, giving thanks | εὐχαριστέω/εὐχαριστία is ordinary "thanks" |
| en | communion | sharing, participation, partnership | κοινωνία |
| en | saint | holy one | ἅγιος as substantive; never a title |
| en | saints | holy ones | inflection |
| en | christ | Anointed, Messiah | Χριστός = "anointed" (מָשִׁיחַ); prose may explain that it later became a name |
| en | christs | anointed ones, messiahs | ψευδόχριστοι (Matt.24.24) |
| en | apostle | sent one, envoy | ἀπόστολος (NT 80); verb ἀποστέλλω "send" |
| en | apostles | sent ones, envoys | inflection |
| en | apostleship | commission, being sent | ἀποστολή |
| en | gospel | good news | εὐαγγέλιον (NT 77) |
| en | gospels | good news (pl.) | inflection |
| en | evangelist | bringer of good news | εὐαγγελιστής |
| en | evangelists | bringers of good news | inflection |
| en | hell | Hades / Gehenna / Sheol / Tartarus — name which | ᾍδης (NT 10), γέεννα (NT 12), שְׁאוֹל, ταρταρόω; never merge them |
| en | bishop | overseer | ἐπίσκοπος (NT 7, LXX 13) |
| en | bishops | overseers | inflection |
| en | deacon | servant, attendant | διάκονος |
| en | deacons | servants, attendants | inflection |
| en | pastor | shepherd | ποιμήν |
| en | pastors | shepherds | inflection |
| en | calvary | Skull, Skull Place | Κρανίον (Luke.23.33); Latin *calvaria* |
| en | easter | Passover | πάσχα (KJV Acts.12.4) |
| en | lucifer | shining one, morning star | הֵילֵל (Isa.14.12); Latin |
| en | jehovah | YHWH (say which convention: Yahweh / the LORD) | hybrid of YHWH consonants + Adonai vowels |
| en | charity | love | ἀγάπη (KJV 1Cor.13) |
| en | gentiles | nations, peoples | ἔθνη / גּוֹיִם |
| en | gentile | of the nations, non-Israelite | singular/adjective |
| en | incarnation | — | describe the verse's words (e.g. σὰρξ ἐγένετο "became flesh") |
| en | original sin | — | no such phrase |
| en | purgatory | — | no such word |
| es | iglesia | asamblea, congregación reunida | ἐκκλησία; NT 114 (SBL; TR 116), LXX 77 (co-ocurre con קָהָל 66×) |
| es | iglesias | asambleas | plural |
| es | bautizar | sumergir, lavar — decir cuál muestra el contexto | βαπτίζω; LXX 2Kgs.5.14 Naamán en el Jordán; Luke.11.38 y Mark.7.4 de lavarse antes de comer |
| es | bautizado | sumergido, lavado | inflexión |
| es | bautizados | sumergidos, lavados | inflexión |
| es | bautizada | sumergida, lavada | inflexión |
| es | bautizadas | sumergidas, lavadas | inflexión |
| es | bautizó | sumergió, lavó | inflexión |
| es | bautizaba | sumergía, lavaba | inflexión |
| es | bautizaban | sumergían, lavaban | inflexión |
| es | bautizaron | sumergieron, lavaron | inflexión |
| es | bautizando | sumergiendo, lavando | inflexión |
| es | bautiza | sumerge, lava | inflexión |
| es | bautizan | sumergen, lavan | inflexión |
| es | bautizará | sumergirá, lavará | inflexión |
| es | bauticen | sumerjan, laven | inflexión |
| es | bautícense | sumérjanse, lávense | inflexión |
| es | bautízate | sumérgete, lávate | inflexión |
| es | bautizarse | sumergirse, lavarse | inflexión |
| es | bautícese | sumérjase | inflexión (RV1909 Acts.2.38) |
| es | bautizándolos | sumergiéndolos | inflexión (RV1909 Matt.28.19) |
| es | bautismo | inmersión, lavamiento | βάπτισμα |
| es | bautismos | inmersiones, lavamientos | plural |
| es | bautista | el que sumergía/lavaba | ὁ βαπτιστής |
| es | bautiz* | sumergir, lavar (cualquier forma) | raíz: bautizo, bautizad, bautizarlos … |
| es | bautíz* | sumergir, lavar | raíz con tilde: bautízate, bautízalos |
| es | bautic* | sumergir, lavar | raíz: bautice, bauticen, bautícese (sin tilde) |
| es | bautíc* | sumergir, lavar | raíz con tilde: bautícense |
| es | bautis* | inmersión, lavamiento | raíz: bautismo, bautismal, bautista |
| es | evangeli* | buena noticia, anunciar la buena noticia | raíz: evangelio, evangelizar, evangelista … (εὐαγγελ-) |
| es | trinidad | — (no hay palabra en el texto) | describir lo que dice el versículo |
| es | trino | — | igual |
| es | sacramento | — | latín *sacramentum*; el griego cercano suele ser μυστήριον |
| es | rapto | ser arrebatado | ἁρπάζω (1Thess.4.17) |
| es | eucaristía | acción de gracias | εὐχαριστέω |
| es | santa cena | cena del señor (1Cor.11.20) | κυριακὸν δεῖπνον; "santa" no está en el texto |
| es | misa | — | no está en el texto |
| es | cristo | Ungido, Mesías | Χριστός = "ungido" (מָשִׁיחַ) |
| es | cristos | ungidos, mesías | ψευδόχριστοι (Matt.24.24) |
| es | jesucristo | Jesús el Ungido / Jesús Mesías | fusión tradicional de nombre + título |
| es | apóstol | enviado | ἀπόστολος |
| es | apóstoles | enviados | inflexión |
| es | evangelio | buena noticia | εὐαγγέλιον |
| es | evangelios | buenas noticias | plural |
| es | evangelista | portador de la buena noticia | εὐαγγελιστής |
| es | evangelistas | portadores de la buena noticia | plural |
| es | infierno | Hades / Gehena / Seol / Tártaro — nombrar cuál | nunca fusionarlos |
| es | obispo | supervisor | ἐπίσκοπος |
| es | obispos | supervisores | plural |
| es | diácono | servidor | διάκονος |
| es | diáconos | servidores | plural |
| es | calvario | (lugar de la) Calavera | Κρανίον (Luke.23.33) |
| es | lucifer | lucero, el resplandeciente | הֵילֵל (Isa.14.12) |
| es | jehová | YHWH (decir la convención: Yahvé / el SEÑOR) | forma híbrida |
| es | caridad | amor | ἀγάπη |
| es | verbo | palabra | λόγος (RV1909 John.1.1 "el Verbo"). Kept although also a grammar term: a `Literal:`/`Natural:` line never needs the grammatical sense |
| es | doctrinad | hagan discípulos | μαθητεύσατε (RV1909 Matt.28.19) |
| es | encarnación | — | describir las palabras del versículo |
| es | pecado original | — | no existe la frase |
| es | purgatorio | — | no está en el texto |

Evidence commands: `lookup.py verse Luke.11.38|Mark.7.4|Mark.6.14|Heb.6.2|Matt.24.24`, `word ἀποστολή`, `compare Eccl.4.1|Lam.1.16`, `word ἐκκλησία`, `usage ἐκκλησία`, `usage βαπτίζω`, `word ᾅδης`, `word γέεννα`, `word ἐπίσκοπος`, `word θεότης`, `compare Matt.16.18`, `compare Acts.2.38`, `compare Matt.28.19`, `compare John.1.1`.
