# les_outils_de_coco

Collection d'outils Windows perso, chacun dans son propre dossier a la racine. Pas de monorepo partage : chaque outil a son `requirements.txt` et son `.bat` de lancement independants.

## Convention commune a tous les outils

- Pas de venv, pas de PyInstaller. Chaque outil se lance via un `.bat` qui :
  1. detecte `python` puis `py` en fallback (certaines machines n'ont que l'un des deux dans le PATH) ;
  2. fait `pip install -r requirements.txt` (essai global, puis `--user` si l'install globale echoue, ex. Python installe "pour tous les utilisateurs" sans droits admin) ;
  3. lance le script directement avec l'interpreteur systeme.
- **Pourquoi pas PyInstaller** : les .exe produits (surtout en `--onefile`) sont quasi systematiquement bloques par SmartScreen/Defender car le bootloader d'auto-extraction ressemble a un comportement de packer/malware, sans lien avec la qualite du code. On a explicitement abandonne cette voie (voir historique git de `site_coco/`) plutot que de payer un certificat de signature de code.
- Une alternative "Python embeddable portable" (dossier autonome avec Python embarque, sans rien installer sur la machine cible) a ete prototypee puis **abandonnee sur demande explicite de l'utilisateur** : il prefere la simplicite (le PC cible a deja Python d'installe) a la portabilite totale. Ne pas la re-proposer sans qu'on te le demande.
- Piege PowerShell 5.1 rencontre pendant ce prototypage : `Set-Content -Encoding utf8` ajoute un BOM UTF-8, ce qui corrompt un fichier `._pth` de Python embeddable (`Failed to import encodings module`). Si ce sujet revient, utiliser `-Encoding ASCII` ou `[System.Text.UTF8Encoding]::new($false)`.
- `.gitignore` racine centralise les exclusions (`*.db`, `__pycache__/`, artefacts PyInstaller, dossiers de sortie generes par chaque outil). Ajouter les nouvelles regles ici plutot que par outil.

## site_coco/ — "MesComptes"

App Flask locale (suivi de depenses perso), mono-utilisateur, lancee via `lancer.bat` -> `python main.py`. Le serveur demarre sur `127.0.0.1:5000` et ouvre le navigateur automatiquement (`main.py`). La base `depenses.db` est creee a cote de `database.py`, une par utilisateur/machine, jamais versionnee.

Point d'attention connu, **laisse tel quel a la demande de l'utilisateur** : `app.py` contient un token GitHub en clair (`GITHUB_QUOTES_TOKEN`) utilise pour recuperer des citations depuis un repo GitHub. L'utilisateur sait que c'est un secret en dur et a decide de ne pas le sortir du code car le repo est prive et le token peu sensible. Ne pas re-proposer de le corriger sauf si le contexte change (ex. le repo devient public).

## PDF_fusion/

Fusionne tous les fichiers deposes dans `a_fusionner/` (pdf, images, `.docx`/`.doc`) en un seul `fusion.pdf` a la racine du dossier, via `fusionner.bat` -> `fusionner.py`. Tri alphabetique des fichiers pour l'ordre de fusion (l'utilisateur peut prefixer les noms `01_`, `02_`... pour forcer l'ordre).

- La conversion Word necessite **Microsoft Word installe** sur la machine (utilise `docx2pdf`, qui pilote Word via COM/`pywin32`). Sans Word, les fichiers `.docx`/`.doc` sont ignores avec un message d'erreur, le reste de la fusion continue normalement.
- Les fichiers types non geres sont ignores (liste affichee en fin d'execution), la fusion ne plante pas dessus.
- `a_fusionner/*` et `fusion.pdf` sont ignores par git (contenu personnel + sortie generee).
