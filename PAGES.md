# Portalul de descărcare

Site-ul static este în `docs/`. Are descărcări CSV, JSON, GeoJSON, tabel cu căutare,
hartă Leaflet, surse, acoperire, dimensiuni și SHA-256, plus exemple curl, Python,
Go și Node.js. Nu necesită backend sau chei API.

```sh
python scripts/build_site.py
python scripts/validate_exports.py
python -m http.server --directory docs 8000
```

Deschide `http://localhost:8000`. Deschiderea `docs/index.html` direct ca fișier
nu permite încărcarea JSON prin `fetch` în unele browsere.

## Repository public, site public

Codul și datele sunt publice. La publicarea site-ului se încarcă numai
conținutul `docs/`, fără cache sau fișiere temporare. GitHub Pages este
disponibil pentru repository-uri publice și în planul GitHub Free.

Cu GitHub CLI autentificat:

```sh
bash scripts/publish.sh          # creează/push repository public
bash scripts/publish.sh --pages  # în plus, activează/publică site-ul public
```

Alternativ, creează repository-ul public în interfața GitHub, încarcă proiectul,
selectează **Settings → Pages → Source: Deploy from a branch**, apoi **main** și
**/docs** și apasă **Save**. Fișierele deja construite din `docs/` se publică
prin mecanismul standard GitHub Pages. După modificarea datelor, rulează din nou
`python scripts/build_site.py` și comite atât datele, cât și `docs/`.

Workflow-ul opțional `Publish GitHub Pages` din `Actions` rămâne disponibil
pentru cazul în care alegi explicit sursa **GitHub Actions**. Nu există
reextragere programată a datelor.

Portal public: https://baditaflorin.github.io/arad-complaints-data/

## Exemple

Toate cele patru exemple acceptă URL-ul ca prim argument și calea de ieșire ca
al doilea. Nu necesită biblioteci externe. Pentru test local:

```sh
sh examples/download.sh http://localhost:8000/data/records.json /tmp/arad-curl.json
python examples/download.py http://localhost:8000/data/records.json /tmp/arad-python.json
go run examples/download.go http://localhost:8000/data/records.json /tmp/arad-go.json
node examples/download.mjs http://localhost:8000/data/records.json /tmp/arad-node.json
```

Înlocuiește extensia URL-ului cu `.csv` sau `.geojson` pentru celelalte formate.
Exemplele care parsează JSON așteaptă array-ul din `records.json`, nu un
FeatureCollection GeoJSON. Pentru schema fiecărui set vezi `data/schema.json`.

## Geometrie și reutilizare

GeoJSON folosește WGS84 și ordinea `[longitudine, latitudine]`. Coordonatele
necunoscute rămân `null`. Un reper pe o stradă nu este o localizare exactă a
unei parcări sau clădiri. Pentru metodă, acoperire, limitări și licențe vezi
`README.md`, `DATA_LICENSE.md` și `data/metadata.json`.

Leaflet 1.9.4 este inclus local cu licența sa BSD; fundalul hărții este furnizat
de OpenStreetMap și necesită internet. Datele OpenStreetMap au condiții ODbL și
atribuire separată. Fonturile web sunt opționale; interfața are fallback local.
