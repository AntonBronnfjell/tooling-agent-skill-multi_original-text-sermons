# Tradition vocabulary

Later church words that the Hebrew/Aramaic/Greek text never literally says. **On `Literal:` and `Natural:` lines these terms are errors** (`check_sermon.py`, case-insensitive whole-word match on the `term` column). In prose and Notes they may be named and discussed — e.g. "the word many Bibles render *church* is ἐκκλησία, an assembly".

Rules for this table:

- `term` is the only machine-read column. One word form per row (matching is whole-word, so inflections need their own rows).
- A term belongs here only if its plain rendering is defensible from the original word. Capitalization-only issues (*Holy Spirit* vs *holy spirit*, *Espíritu Santo* vs *espíritu santo*, *Hijo*, *Verbo*-as-title) cannot be matched case-insensitively and live in `fidelity-rules.md` instead.
- Words that are ordinary plain renderings in the target language stay out even if churches also use them (es *santo* = "holy", *pastor* = "shepherd", *Pascua* = Passover in Spanish).
- Counts and LXX notes below come from `lookup.py word`/`usage` output; LXX figures are same-verse co-occurrence, not alignment.

| lang | term | plain rendering | note |
|---|---|---|---|
| en | church | assembly, gathering | ἐκκλησία; NT 117, LXX 77 (co-occurs with קָהָל 66×); also a civic assembly (Acts.19.32) |
| en | churches | assemblies | plural of the above |
| en | baptize | immerse, dip | βαπτίζω; LXX 2Kgs.5.14 Naaman "dipped himself" in the Jordan; Josephus of sinking ships |
| en | baptized | immersed, dipped | inflection |
| en | baptizing | immersing | inflection |
| en | baptism | immersion | βάπτισμα |
| en | baptist | immerser | ὁ βαπτιστής (John) |
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
| en | apostle | sent one, envoy | ἀπόστολος (NT 80); verb ἀποστέλλω "send" |
| en | apostles | sent ones, envoys | inflection |
| en | repent | change one's mind, turn | μετανοέω; LXX co-occurs with נָחַם 14×, שׁוּב 9× |
| en | repentance | change of mind, turning | μετάνοια |
| en | repented | changed their mind, turned | inflection |
| en | gospel | good news | εὐαγγέλιον (NT 77) |
| en | evangelist | bringer of good news | εὐαγγελιστής |
| en | hell | Hades / Gehenna / Sheol / Tartarus — name which | ᾍδης (NT 10), γέεννα (NT 12), שְׁאוֹל, ταρταρόω; never merge them |
| en | bishop | overseer | ἐπίσκοπος (NT 7, LXX 13) |
| en | deacon | servant, attendant | διάκονος |
| en | pastor | shepherd | ποιμήν |
| en | pastors | shepherds | inflection |
| en | calvary | Skull, Skull Place | Κρανίον (Luke.23.33); Latin *calvaria* |
| en | easter | Passover | πάσχα (KJV Acts.12.4) |
| en | lucifer | shining one, morning star | הֵילֵל (Isa.14.12); Latin |
| en | jehovah | YHWH (say which convention: Yahweh / the LORD) | hybrid of YHWH consonants + Adonai vowels |
| en | comforter | helper, advocate, one called alongside | παράκλητος |
| en | charity | love | ἀγάπη (KJV 1Cor.13) |
| en | gentiles | nations, peoples | ἔθνη / גּוֹיִם |
| en | incarnation | — | describe the verse's words (e.g. σὰρξ ἐγένετο "became flesh") |
| en | original sin | — | no such phrase |
| en | purgatory | — | no such word |
| es | iglesia | asamblea, congregación reunida | ἐκκλησία; NT 117, LXX 77 (co-ocurre con קָהָל 66×) |
| es | iglesias | asambleas | plural |
| es | bautizar | sumergir | βαπτίζω; LXX 2Kgs.5.14 Naamán "se sumergió" |
| es | bautizado | sumergido | inflexión |
| es | bautizados | sumergidos | inflexión |
| es | bautícese | sumérjase | inflexión (RV1909 Acts.2.38) |
| es | bautizándolos | sumergiéndolos | inflexión (RV1909 Matt.28.19) |
| es | bautismo | inmersión | βάπτισμα |
| es | bautista | el que sumergía | ὁ βαπτιστής |
| es | trinidad | — (no hay palabra en el texto) | describir lo que dice el versículo |
| es | trino | — | igual |
| es | sacramento | — | latín *sacramentum*; el griego cercano suele ser μυστήριον |
| es | rapto | ser arrebatado | ἁρπάζω (1Thess.4.17) |
| es | eucaristía | acción de gracias | εὐχαριστέω |
| es | santa cena | cena del Señor (1Cor.11.20) | κυριακὸν δεῖπνον; "santa" no está en el texto |
| es | misa | — | no está en el texto |
| es | cristo | Ungido, Mesías | Χριστός = "ungido" (מָשִׁיחַ) |
| es | jesucristo | Jesús el Ungido / Jesús Mesías | fusión tradicional de nombre + título |
| es | apóstol | enviado | ἀπόστολος |
| es | apóstoles | enviados | inflexión |
| es | arrepentirse | cambiar de mentalidad, volverse | μετανοέω |
| es | arrepentíos | cambien de mentalidad, vuélvanse | inflexión (RV1909 Acts.2.38) |
| es | arrepentimiento | cambio de mentalidad, vuelta | μετάνοια |
| es | evangelio | buena noticia | εὐαγγέλιον |
| es | evangelista | portador de la buena noticia | εὐαγγελιστής |
| es | infierno | Hades / Gehena / Seol / Tártaro — nombrar cuál | nunca fusionarlos |
| es | obispo | supervisor | ἐπίσκοπος |
| es | diácono | servidor | διάκονος |
| es | calvario | (lugar de la) Calavera | Κρανίον (Luke.23.33) |
| es | lucifer | lucero, el resplandeciente | הֵילֵל (Isa.14.12) |
| es | jehová | YHWH (decir la convención: Yahvé / el SEÑOR) | forma híbrida |
| es | consolador | ayudador, abogado | παράκλητος |
| es | caridad | amor | ἀγάπη |
| es | verbo | palabra | λόγος (RV1909 John.1.1 "el Verbo") |
| es | gentiles | naciones, pueblos | ἔθνη / גּוֹיִם (RV1909 Matt.28.19) |
| es | doctrinad | hagan discípulos | μαθητεύσατε (RV1909 Matt.28.19) |
| es | encarnación | — | describir las palabras del versículo |
| es | pecado original | — | no existe la frase |
| es | purgatorio | — | no está en el texto |

Evidence commands: `lookup.py word ἐκκλησία`, `usage ἐκκλησία`, `usage βαπτίζω`, `word μετανοέω`, `word ᾅδης`, `word γέεννα`, `word ἐπίσκοπος`, `word θεότης`, `compare Matt.16.18`, `compare Acts.2.38`, `compare Matt.28.19`, `compare John.1.1`.
