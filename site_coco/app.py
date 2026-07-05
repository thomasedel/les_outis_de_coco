from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import get_connection, init_db
from datetime import datetime, date
import os
import json
import random
try:
    import requests as http_requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ─────────────────────────────────────────────
# QUOTES DEPUIS GITHUB — Cache RAM
# ─────────────────────────────────────────────

# URLs via l'API GitHub (bypass le CDN raw.githubusercontent.com qui cache agressivement)
GITHUB_QUOTES_URL   = 'https://api.github.com/repos/thomasedel/app_quotes/contents/coco_quotes.json'
GITHUB_CONFIG_URL   = 'https://api.github.com/repos/thomasedel/app_quotes/contents/config.json'
GITHUB_QUOTES_TOKEN = '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'

DEV_PASSWORD = 'coco2024'

QUOTES_CACHE_TTL = 60   # rafraîchit les quotes toutes les 60 sec
CONFIG_CACHE_TTL  = 60  # rafraîchit le config toutes les 60 sec

# Cache des quotes
_cache = {
    'quotes': [],        # liste chargée depuis GitHub
    'last_fetch': 0,     # timestamp du dernier fetch réussi
    'last_error': None,  # message d'erreur du dernier fetch
    'last_attempt': 0,   # timestamp de la dernière tentative (succès ou échec)
}

# Cache du config distant
_config_cache = {
    'actif': True,       # afficher les quotes
    'frequence': 1.0,    # probabilité d'affichage (0.0 → 1.0)
    'last_attempt': 0,
    'last_error': None,
}


def _get_remote_config():
    """
    Charge actif/frequence depuis GitHub config.json (TTL 5 min).
    Met à jour _config_cache en place. Silencieux en cas d'échec.
    """
    import time
    if not REQUESTS_OK:
        return

    now = time.time()
    if now - _config_cache['last_attempt'] < CONFIG_CACHE_TTL:
        return  # cache encore valide

    _config_cache['last_attempt'] = now
    headers = {
        'Authorization': f'token {GITHUB_QUOTES_TOKEN}',
        'Accept': 'application/vnd.github.v3.raw',
        'Cache-Control': 'no-cache',
    }
    try:
        resp = http_requests.get(GITHUB_CONFIG_URL, headers=headers, timeout=4)
        resp.raise_for_status()
        data = resp.json()
        _config_cache['actif']      = bool(data.get('actif', True))
        _config_cache['frequence']  = float(data.get('frequence', 1.0))
        _config_cache['last_error'] = None
    except Exception as e:
        _config_cache['last_error'] = str(e)


def _fetch_quotes_from_github():
    """Charge la liste complète depuis GitHub. Retourne (list, error_msg)."""
    if not REQUESTS_OK:
        return [], 'Module requests non installé'

    headers = {
        'Authorization': f'token {GITHUB_QUOTES_TOKEN}',
        'Accept': 'application/vnd.github.v3.raw',
        'Cache-Control': 'no-cache',
    }

    try:
        resp = http_requests.get(GITHUB_QUOTES_URL, headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        return [], f'Erreur HTTP : {e}'

    try:
        # Avec vnd.github.v3.raw, la réponse est toujours le contenu brut du fichier
        filename = GITHUB_QUOTES_URL.split('/')[-1]
        if filename.endswith('.json'):
            quotes = resp.json()
        else:
            lignes = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
            quotes = [{'texte': l, 'auteur': 'Anonyme'} for l in lignes]
    except Exception as e:
        return [], f'Erreur de parsing : {e}'

    if not quotes:
        return [], 'Fichier vide'

    return quotes, None



def get_quote():
    """
    Retourne une citation aléatoire depuis le cache RAM.
    - Rafraîchit le config distant toutes les 5 min (actif, frequence).
    - Rafraîchit les quotes toutes les 30 min.
    - Retourne (quote_dict | None, error_msg | None).
    """
    import time
    now = time.time()

    # 1. Toujours rafraîchir le config distant si TTL expiré
    _get_remote_config()

    # 2. Si désactivé → rien
    if not _config_cache['actif']:
        return None, None

    # 3. Rafraîchir les quotes si périmées
    if now - _cache['last_attempt'] >= QUOTES_CACHE_TTL:
        _cache['last_attempt'] = now
        quotes, error = _fetch_quotes_from_github()
        if quotes:
            _cache['quotes'] = quotes
            _cache['last_fetch'] = now
            _cache['last_error'] = None
        else:
            _cache['last_error'] = error

    if not _cache['quotes']:
        return None, _cache['last_error'] or 'Aucune citation disponible'

    # 4. Appliquer la fréquence (tirage aléatoire)
    if random.random() > _config_cache['frequence']:
        return None, None  # pas de chance cette fois

    return random.choice(_cache['quotes']), _cache['last_error']


def get_cache_info():
    """Retourne des infos de diagnostic sur le cache quotes et config."""
    import time
    now = time.time()
    return {
        'nb_quotes': len(_cache['quotes']),
        'last_error': _cache['last_error'],
        'last_fetch': _cache['last_fetch'],
        'last_attempt': _cache['last_attempt'],
        'ttl_remaining': max(0, int(QUOTES_CACHE_TTL - (now - _cache['last_attempt']))),
        # Config distant
        'actif': _config_cache['actif'],
        'frequence': _config_cache['frequence'],
        'config_error': _config_cache['last_error'],
        'config_ttl_remaining': max(0, int(CONFIG_CACHE_TTL - (now - _config_cache['last_attempt']))),
    }



def get_repo_contents():
    """
    Liste les fichiers du repo GitHub via l'API Contents.
    Retourne (liste_fichiers, erreur).
    """
    if not REQUESTS_OK:
        return [], 'requests non disponible'

    # Extraire owner/repo depuis l'URL API
    # Format : https://api.github.com/repos/OWNER/REPO/contents/fichier
    try:
        parts = GITHUB_QUOTES_URL.replace('https://api.github.com/repos/', '').split('/')
        owner, repo = parts[0], parts[1]
    except Exception:
        return [], f'Impossible de parser l\'URL : {GITHUB_QUOTES_URL}'

    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/'
    headers = {
        'Authorization': f'token {GITHUB_QUOTES_TOKEN}',
        'Accept': 'application/vnd.github+json',
    }

    try:
        resp = http_requests.get(api_url, headers=headers, timeout=5)
        resp.raise_for_status()
        items = resp.json()
        return [
            {'name': i['name'], 'type': i['type'], 'size': i.get('size', 0)}
            for i in items
        ], None
    except Exception as e:
        return [], f'Erreur API GitHub : {e}'



def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static')
    )
    app.secret_key = 'mes_comptes_secret_2024'

    init_db()

    # ─────────────────────────────────────────────
    # ROUTES PRINCIPALES
    # ─────────────────────────────────────────────

    @app.route('/')
    def index():
        conn = get_connection()

        # Citation du jour
        quote, quote_error = get_quote()

        # Total global
        total = conn.execute(
            'SELECT COALESCE(SUM(montant), 0) as total FROM depenses'
        ).fetchone()['total']

        # Résumé par catégorie
        resume = conn.execute('''
                              SELECT c.nom,
                                     c.couleur,
                                     COUNT(d.id)                 as nb_depenses,
                                     COALESCE(SUM(d.montant), 0) as total_cat
                              FROM categories c
                                       LEFT JOIN depenses d ON d.categorie_id = c.id
                              GROUP BY c.id, c.nom, c.couleur
                              ORDER BY total_cat DESC
                              ''').fetchall()

        # Dernières dépenses
        dernieres = conn.execute('''
                                 SELECT d.*, c.nom as categorie_nom, c.couleur
                                 FROM depenses d
                                          LEFT JOIN categories c ON c.id = d.categorie_id
                                 ORDER BY d.created_at DESC LIMIT 5
                                 ''').fetchall()

        conn.close()

        return render_template('index.html',
                               total=total,
                               resume=resume,
                               dernieres=dernieres,
                               quote=quote
                               )

    # ─────────────────────────────────────────────
    # DÉPENSES
    # ─────────────────────────────────────────────

    @app.route('/depenses')
    def depenses():
        conn = get_connection()

        # Filtres
        categorie_filtre = request.args.get('categorie', '')
        mois_filtre = request.args.get('mois', '')

        query = '''
                SELECT d.*, c.nom as categorie_nom, c.couleur
                FROM depenses d
                         LEFT JOIN categories c ON c.id = d.categorie_id
                WHERE 1 = 1 \
                '''
        params = []

        if categorie_filtre:
            query += ' AND d.categorie_id = ?'
            params.append(categorie_filtre)
        if mois_filtre:
            query += ' AND strftime("%Y-%m", d.date) = ?'
            params.append(mois_filtre)

        query += ' ORDER BY d.date DESC, d.created_at DESC'

        liste = conn.execute(query, params).fetchall()
        categories = conn.execute('SELECT * FROM categories ORDER BY nom').fetchall()

        total_filtre = sum(d['montant'] for d in liste)

        conn.close()

        return render_template('depenses.html',
                               depenses=liste,
                               categories=categories,
                               total_filtre=total_filtre,
                               categorie_filtre=categorie_filtre,
                               mois_filtre=mois_filtre,
                               today=date.today().isoformat()
                               )

    @app.route('/depenses/ajouter', methods=['POST'])
    def ajouter_depense():
        description = request.form.get('description', '').strip()
        montant = request.form.get('montant', '').strip()
        categorie_id = request.form.get('categorie_id', '').strip()
        date_depense = request.form.get('date', '').strip()

        # Validation
        erreurs = []
        if not description:
            erreurs.append('La description est obligatoire.')
        if not montant:
            erreurs.append('Le montant est obligatoire.')
        else:
            try:
                montant = float(montant.replace(',', '.'))
                if montant <= 0:
                    erreurs.append('Le montant doit être positif.')
            except ValueError:
                erreurs.append('Le montant est invalide.')
        if not date_depense:
            date_depense = date.today().isoformat()

        if erreurs:
            for e in erreurs:
                flash(e, 'erreur')
            return redirect(url_for('depenses'))

        conn = get_connection()
        conn.execute(
            'INSERT INTO depenses (description, montant, categorie_id, date) VALUES (?, ?, ?, ?)',
            (description, montant, categorie_id or None, date_depense)
        )
        conn.commit()
        conn.close()

        flash('Dépense ajoutée avec succès !', 'succes')
        return redirect(url_for('depenses'))

    @app.route('/depenses/supprimer/<int:id>', methods=['POST'])
    def supprimer_depense(id):
        conn = get_connection()
        conn.execute('DELETE FROM depenses WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Dépense supprimée.', 'succes')
        return redirect(url_for('depenses'))

    # ─────────────────────────────────────────────
    # CATÉGORIES
    # ─────────────────────────────────────────────

    @app.route('/categories')
    def categories():
        conn = get_connection()
        cats = conn.execute('''
                            SELECT c.*, COUNT(d.id) as nb_depenses
                            FROM categories c
                                     LEFT JOIN depenses d ON d.categorie_id = c.id
                            GROUP BY c.id
                            ORDER BY c.nom
                            ''').fetchall()
        conn.close()
        return render_template('categories.html', categories=cats)

    @app.route('/categories/ajouter', methods=['POST'])
    def ajouter_categorie():
        nom = request.form.get('nom', '').strip()
        couleur = request.form.get('couleur', '#3498db')

        if not nom:
            flash('Le nom est obligatoire.', 'erreur')
            return redirect(url_for('categories'))

        conn = get_connection()
        try:
            conn.execute(
                'INSERT INTO categories (nom, couleur) VALUES (?, ?)',
                (nom, couleur)
            )
            conn.commit()
            flash(f'Catégorie "{nom}" créée !', 'succes')
        except Exception:
            flash(f'La catégorie "{nom}" existe déjà.', 'erreur')
        finally:
            conn.close()

        return redirect(url_for('categories'))

    @app.route('/categories/supprimer/<int:id>', methods=['POST'])
    def supprimer_categorie(id):
        conn = get_connection()
        # Remettre les dépenses liées à "sans catégorie"
        conn.execute(
            'UPDATE depenses SET categorie_id = NULL WHERE categorie_id = ?', (id,)
        )
        conn.execute('DELETE FROM categories WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Catégorie supprimée.', 'succes')
        return redirect(url_for('categories'))

    @app.route('/categories/modifier/<int:id>', methods=['POST'])
    def modifier_categorie(id):
        nom = request.form.get('nom', '').strip()
        couleur = request.form.get('couleur', '#3498db')

        if not nom:
            flash('Le nom est obligatoire.', 'erreur')
            return redirect(url_for('categories'))

        conn = get_connection()
        conn.execute(
            'UPDATE categories SET nom = ?, couleur = ? WHERE id = ?',
            (nom, couleur, id)
        )
        conn.commit()
        conn.close()
        flash('Catégorie mise à jour.', 'succes')
        return redirect(url_for('categories'))

    # ─────────────────────────────────────────────
    # RÉSUMÉ MENSUEL
    # ─────────────────────────────────────────────

    @app.route('/resume')
    def resume():
        conn = get_connection()

        # Mois/année sélectionnés (défaut = mois courant)
        today = date.today()
        mois = request.args.get('mois', str(today.month).zfill(2))
        annee = request.args.get('annee', str(today.year))

        mois_annee = f"{annee}-{mois}"

        # Total du mois
        total_mois = conn.execute(
            "SELECT COALESCE(SUM(montant), 0) as total FROM depenses WHERE strftime('%Y-%m', date) = ?",
            (mois_annee,)
        ).fetchone()['total']

        # Total par catégorie pour ce mois
        resume_cat = conn.execute('''
            SELECT c.nom,
                   c.couleur,
                   COUNT(d.id) as nb_depenses,
                   COALESCE(SUM(d.montant), 0) as total_cat
            FROM categories c
                     LEFT JOIN depenses d
                               ON d.categorie_id = c.id
                                   AND strftime('%Y-%m', d.date) = ?
            GROUP BY c.id, c.nom, c.couleur
            HAVING total_cat > 0
            ORDER BY total_cat DESC
        ''', (mois_annee,)).fetchall()

        # Dépenses sans catégorie pour ce mois
        sans_cat_total = conn.execute(
            "SELECT COALESCE(SUM(montant), 0) as total FROM depenses WHERE categorie_id IS NULL AND strftime('%Y-%m', date) = ?",
            (mois_annee,)
        ).fetchone()['total']

        # Détail de toutes les dépenses du mois
        depenses_mois = conn.execute('''
            SELECT d.*, c.nom as categorie_nom, c.couleur
            FROM depenses d
                     LEFT JOIN categories c ON c.id = d.categorie_id
            WHERE strftime('%Y-%m', d.date) = ?
            ORDER BY d.date DESC, d.created_at DESC
        ''', (mois_annee,)).fetchall()

        # Liste des mois ayant des dépenses (pour le sélecteur)
        mois_disponibles = conn.execute('''
            SELECT DISTINCT strftime('%Y', date) as annee,
                            strftime('%m', date) as mois
            FROM depenses
            ORDER BY annee DESC, mois DESC
        ''').fetchall()

        conn.close()

        noms_mois = {
            '01': 'Janvier', '02': 'Février', '03': 'Mars',
            '04': 'Avril', '05': 'Mai', '06': 'Juin',
            '07': 'Juillet', '08': 'Août', '09': 'Septembre',
            '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
        }

        return render_template('resume.html',
                               total_mois=total_mois,
                               resume_cat=resume_cat,
                               sans_cat_total=sans_cat_total,
                               depenses_mois=depenses_mois,
                               mois=mois,
                               annee=annee,
                               mois_annee=mois_annee,
                               noms_mois=noms_mois,
                               mois_disponibles=mois_disponibles,
                               today=today
                               )

    # ─────────────────────────────────────────────
    # PAGE DEV (cachée, diagnostic)
    # ─────────────────────────────────────────────

    @app.route('/dev')
    def dev():
        if request.args.get('pwd') != DEV_PASSWORD:
            return render_template('dev_denied.html'), 403
        # Force le refresh complet pour voir l'état réel de GitHub
        _cache['last_attempt'] = 0
        _config_cache['last_attempt'] = 0
        quote, quote_error = get_quote()
        cache = get_cache_info()
        repo_files, repo_error = get_repo_contents()
        return render_template('dev.html',
                               quote=quote,
                               quote_error=quote_error,
                               quotes_url=GITHUB_QUOTES_URL,
                               config_url=GITHUB_CONFIG_URL,
                               requests_ok=REQUESTS_OK,
                               cache=cache,
                               repo_files=repo_files,
                               repo_error=repo_error
                               )

    return app
