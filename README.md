# Arad — sesizări publice MyArad

Date gata de descărcat și cod pentru reproducerea unei proiecții a hărții publice
de sesizări a Primăriei Municipiului Arad. Datele includ coordonatele originale ale
marcajelor; nu au fost inventate coordonate și nu a fost necesară geocodarea.

## Descărcări

- [CSV](data/records.csv)
- [JSON — array de înregistrări](data/records.json)
- [GeoJSON — FeatureCollection](data/records.geojson)
- [Metadate, acoperire și limite](data/metadata.json)
- [Schema JSON](data/schema.json)
- [Intrare sanitizată pentru reproducere offline](data/source-snapshot.sanitized.json)

Snapshotul inițial conține **60 de sesizări și 60 de poziții originale**. Numărul
curent, perioada datelor și data extragerii se citesc din `data/metadata.json`.
Acesta este un instantaneu al răspunsului hărții publice, nu istoricul tuturor
sesizărilor transmise vreodată instituției.

## Surse și descoperirea API-ului

1. [Pagina publică de sesizări](https://myarad.primariaarad.ro/dm_arad/servicii.nsf/pagini/sesizari%2Bonline%2Bpe%2Bharta)
   încarcă aplicația Angular `cityline`.
2. Clientul public
   [`sobis.mycity.js`](https://myarad.primariaarad.ro/dm_arad/servicii.nsf/sobis.mycity.js?Open)
   apelează `SobisUtils.serverContext() + '/myCity/getAll'` prin GET.
3. [`sobis.utils.js`](https://myarad.primariaarad.ro/dm_arad/servicii.nsf/sobis.utils.js?Open)
   definește `EXT_SERVICES = 'ext_services.nsf/xsp/.jaxrs'`. Calea instalării este
   `/dm_arad/`, deci endpointul folosit efectiv de hartă este:

```text
https://myarad.primariaarad.ro/dm_arad/ext_services.nsf/xsp/.jaxrs/myCity/getAll
```

Răspunsul conține `metadata`, `total`, `entries` și `config`. Extracția folosește
numai acest endpoint public, fără autentificare, CAPTCHA, cont sau chei Google.
Nu se accesează formulare de depunere ori documente care nu sunt afișate public.

## Reproducere

Necesită Python 3.10 sau mai nou; nu are dependențe externe.

```bash
python scripts/scrape.py --output data
python -m unittest discover -s tests -v
```

Scraperul folosește antetul JSON Accept, Referer-ul paginii publice și parametrul
`_dc`, conform clientului existent. În această sesiune, o cerere fără forma
completă a antetelor a primit 406, iar cererea identică aplicației publice a
funcționat. Dacă instituția mută API-ul, se poate specifica `--endpoint URL`
după verificarea noii adrese publice în clientul oficial.

Reproducerea **fără rețea**, din intrarea sanitizată inclusă:

```bash
python scripts/scrape.py --input data/source-snapshot.sanitized.json --output /tmp/myarad-reproduced
```

Se poate importa și un răspuns JSON original salvat local:

```bash
python scripts/scrape.py --input /cale/raspuns-api.json --output data
```

Fișierele originale pot conține texte personale: păstrați-le în `private/` sau
`tmp/`, directoare ignorate de Git. Scraperul nu salvează răspunsul original;
scrie numai câmpurile sigure de mai jos și o intrare sanitizată reproductibilă.
Pentru importul unui original, timpul de preluare este citit implicit din mtime
al fișierului; `--retrieved-at 2026-11-07T16:00:00Z` permite o dată cunoscută exact.

## Câmpuri și coordonate

| Câmp | Semnificație |
|---|---|
| `id`, `source_id` | ID stabil în export, respectiv ID din harta publică |
| `name` | Etichetă generată exclusiv din categorie, fără textul sesizării |
| `category`, `status` | Categorie controlată și starea publicată de sursă |
| `submitted_at` | Data depunerii în ISO 8601; sursa folosește DD/MM/YYYY |
| `latitude`, `longitude` | Poziția originală din câmpul `position` |
| `geocode_method` | `source_original` sau `missing`; nicio geocodare externă |
| `coordinate_precision` | Marcaj raportat în hartă; precizie nevalidată independent |
| `source_url`, `source_page` | Endpointul snapshotului și pagina oficială |
| `source_sha256`, `retrieved_at` | Amprenta răspunsului original și timpul preluării |

Clientul MyArad tratează `position` ca **[latitudine, longitudine]**; GeoJSON
folosește **[longitudine, latitudine]**. Conversia este testată explicit.
În cazul unui marcaj lipsă sau invalid, ambele coordonate sunt `null`, iar
feature-ul GeoJSON are `geometry: null`. Nicio sesizare nu este plasată artificial
în centrul Aradului. Poziția introdusă de un utilizator nu este o măsurătoare
topografică și nu trebuie tratată ca adevăr verificat la adresă.

## Protecția datelor și limitele snapshotului

Exportul folosește o listă strictă de câmpuri: ID, categorie, stare, dată,
coordonate și proveniență. **Nu include** textul liber `mesaj`, răspunsul
`raspuns`, numele petenților, contacte, fotografii sau alte atașamente. Textele
libere pot identifica persoane chiar și atunci când există deja pe o hartă
publică; din acest motiv sunt omise integral, nu filtrate prin regex.

Configurația API-ului oferă categoriile; valorile necunoscute sunt înlocuite cu
etichete neutre. Stările necunoscute sunt de asemenea înlocuite, pentru a evita
trecerea accidentală a textelor libere în câmpuri presupuse controlate.

Un [document strategic oficial din martie 2022](https://www.primariaarad.ro/dm_arad/portal.nsf/9886ED9671CAD1B5C2258805003EF921/%24FILE/5.%20SIDU%20Arad%202021-2027.%20Martie%202022.pdf?Open=)
descria afișarea sesizărilor nesoluționate timp de 30 de zile și a celor
soluționate timp de 5 zile. Feed-ul obținut în noiembrie 2026 conține și date
mai vechi: nu presupunem că acele ferestre istorice sunt încă aplicate.

`total` este verificat față de numărul de înregistrări primite. O nepotrivire
produce `status: partial`; o pagină HTML de autentificare sau o eroare de rețea
produce cod de ieșire 1 și păstrează exporturile existente, fără a raporta
în mod fals zero sesizări.

## Licență

Codul: MIT. Pentru datele sursei nu a fost identificată o licență explicită de
reutilizare. Consultați [DATA_LICENSE.md](DATA_LICENSE.md). Accesibilitatea
publică a sursei nu este declarată aici drept licență CC0 sau CC BY.

## Site, exemple și publicare

Vezi [PAGES.md](PAGES.md) pentru site-ul static din `docs/`, cele patru exemple
executabile și pașii de publicare. Repository-ul este public; site-ul și descărcările sunt publicate prin GitHub Pages. Sursa, datele și exemplele
sunt disponibile și în arhiva `docs/downloads/source.zip`.
