# -*- coding: utf-8 -*-
from flask import Flask, render_template, g, url_for, send_file, make_response, Response, request, redirect, flash
import sqlite3
import os
import shutil
import zipfile
import webbrowser
import threading
import time
from datetime import datetime, date
from werkzeug.utils import secure_filename, NotFound
from PIL import Image
import csv
from io import StringIO

racine = os.path.dirname(__file__)

def initialiser_base_si_absente():
    chemin_db = os.path.join(racine, "data", "app.db")
    chemin_data = os.path.join(racine, "data")
    if not os.path.exists(chemin_data):
        os.makedirs(chemin_data)

    if not os.path.exists(chemin_db):
        print("Base de données absente. Création en cours...")

        chemin_schema = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(chemin_schema, "r", encoding="utf-8") as f:
            script = f.read()  

        conn = sqlite3.connect(chemin_db)
        cursor = conn.cursor()
        cursor.executescript(script)
        conn.commit()
        conn.close()
        print("Base de données créée avec succès.")



# Initialisation de l'application Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = '#GHSJKEI975SH!' 

# Chemin de la base de données
initialiser_base_si_absente()
DATABASE = os.path.join(racine, 'data', 'app.db')

# Connexion à la base SQLite
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# Ajout a l'historique
def ajouter_historique(type_action, resume, commentaire=None, cible_id=None):
    db = get_db()
    db.execute("""
        INSERT INTO historique (type, resume, commentaire, cible_id)
        VALUES (?, ?, ?, ?)
    """, (type_action, resume, commentaire, cible_id))
    db.commit()


# Fermeture de la base à la fin de chaque requête
@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now}



# Page d'accueil
@app.route('/')
def index():
    boutons = [
        ("Gestion des bateaux", "/bateaux/liste"),
        ("Gestion des emplacements", "/zones/liste"),
        ("Paiements port", "/paiements/port"),
        ("Maintenance club", "/maintenance/liste"),
        ("Fournisseurs", "/fournisseurs/liste"),
        ("Locations", "/locations/liste"),
        ("Membres", "/membres/liste"),
        ("Planning", "/agenda/planning"),
        ("Documents", "/documents/liste"),
        ("Historique", "/historique/interventions"),
        ("Statistiques", "/statistiques/tableau_de_bord"),
        ("Sauvegarde", "/sauvegarde")
    ]
    return render_template('index.html', boutons=boutons)

@app.route('/bateaux/liste')
def liste_bateaux():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()
    est_du_club = request.args.get('club', 'tous')
    page = int(request.args.get('page', 1))
    par_page = 20
    offset = (page - 1) * par_page

    query = "SELECT * FROM bateaux WHERE 1=1"
    params = []

    if recherche:
        query += " AND (nom LIKE ? OR immatriculation LIKE ? OR categorie LIKE ?)"
        recherche_like = f"%{recherche}%"
        params.extend([recherche_like, recherche_like, recherche_like])

    if est_du_club == 'club':
        query += " AND est_du_club = 1"
    elif est_du_club == 'hors_club':
        query += " AND est_du_club = 0"

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total = db.execute(count_query, params).fetchone()[0]

    query += " ORDER BY nom ASC LIMIT ? OFFSET ?"
    params.extend([par_page, offset])

    bateaux = db.execute(query, params).fetchall()
    nb_pages = (total + par_page - 1) // par_page

    return render_template("bateaux/liste.html",
                           bateaux=bateaux,
                           page=page,
                           nb_pages=nb_pages,
                           recherche=recherche,
                           club_filter=est_du_club)

@app.route('/bateaux/ajouter', methods=['GET', 'POST'])
def ajouter_bateau():
    db = get_db()

    if request.method == 'POST':
        # Champs principaux
        nom = request.form['nom']
        nom_proprietaire = request.form['nom_proprietaire']
        constructeur_modele = request.form['constructeur_modele']
        date_arrivee = request.form['date_arrivee'] or None
        type_ = request.form['type']
        taille = request.form['taille'] or None
        couleur_coque = request.form['couleur_coque']
        couleur_pont = request.form['couleur_pont']
        annee = request.form['annee'] or None
        categorie = request.form['categorie']
        est_du_club = 1 if 'est_du_club' in request.form else 0
        remarques = request.form['remarques']
        immatriculation = request.form.get('immatriculation')
        numero_voile = request.form.get('numero_voile')

        # Assurance
        assurance_nom = request.form.get('assurance_nom')
        assurance_numero = request.form.get('assurance_numero')
        assurance_coordonnees = request.form.get('assurance_coordonnees')
        assurance_tel = request.form.get('assurance_tel')

        # Remorque
        remorque_au_club = 1 if 'remorque_au_club' in request.form else 0

        cursor = db.execute("""
            INSERT INTO bateaux (
                nom, nom_proprietaire, constructeur_modele, date_arrivee,
                type, taille, couleur_coque, couleur_pont, annee, categorie,
                est_du_club, remarques, immatriculation, numero_voile,
                assurance_nom, assurance_numero, assurance_coordonnees, assurance_tel,
                remorque_au_club
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nom, nom_proprietaire, constructeur_modele, date_arrivee,
            type_, taille, couleur_coque, couleur_pont, annee, categorie,
            est_du_club, remarques, immatriculation, numero_voile,
            assurance_nom, assurance_numero, assurance_coordonnees, assurance_tel,
            remorque_au_club
        ))

        bateau_id = cursor.lastrowid
        db.commit()

        # Création du dossier bateau
        base_dir = os.path.dirname(__file__)  # ← base du projet
        dossier = os.path.join(base_dir, 'data', 'bateaux', str(bateau_id))
        os.makedirs(dossier, exist_ok=True)

        # Enregistrement de la photo
        photo = request.files.get('photo')
        if photo and photo.filename != '':
            try:
                img = Image.open(photo)
                photo_path = os.path.join(dossier, 'photo.jpg')
                img.convert('RGB').save(photo_path, 'JPEG')
                db.execute("UPDATE bateaux SET photo = ? WHERE id = ?", (photo_path, bateau_id))
            except Exception as e:
                print("Erreur lors de l’enregistrement de la photo :", e)

        # Enregistrement du docx
        docx_file = request.files.get('docx')
        if docx_file and docx_file.filename.endswith('.docx'):
            try:
                docx_path = os.path.join(dossier, 'document.docx')
                docx_file.save(docx_path)
                db.execute("UPDATE bateaux SET docx = ? WHERE id = ?", (docx_path, bateau_id))
            except Exception as e:
                print("Erreur lors de l’enregistrement du document :", e)

        db.commit()
        flash("Bateau ajouté avec succès.")
        ajouter_historique("bateau", f"Ajout du bateau « {nom} »", f"Propriétaire : {nom_proprietaire}", bateau_id)
        return redirect('/bateaux/liste')

    emplacements = db.execute("SELECT id, nom FROM emplacements ORDER BY nom").fetchall()
    membres = db.execute("SELECT id, nom, prenom FROM membres ORDER BY nom").fetchall()

    return render_template('bateaux/formulaire.html', emplacements=emplacements, membres=membres)

@app.route('/bateaux/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_bateau(id):
    db = get_db()
    bateau = db.execute("SELECT * FROM bateaux WHERE id = ?", (id,)).fetchone()

    if not bateau:
        flash("Bateau introuvable.", "danger")
        return redirect('/bateaux/liste')

    if request.method == 'POST':
        # Lecture du formulaire
        nom = request.form['nom']
        nom_proprietaire = request.form['nom_proprietaire']
        constructeur_modele = request.form['constructeur_modele']
        date_arrivee = request.form['date_arrivee'] or None
        type_ = request.form['type']
        taille = request.form['taille'] or None
        couleur_coque = request.form['couleur_coque']
        couleur_pont = request.form['couleur_pont']
        annee = request.form['annee'] or None
        categorie = request.form['categorie']
        est_du_club = 1 if 'est_du_club' in request.form else 0
        remarques = request.form['remarques']
        immatriculation = request.form.get('immatriculation')
        numero_voile = request.form.get('numero_voile')

        assurance_nom = request.form.get('assurance_nom')
        assurance_numero = request.form.get('assurance_numero')
        assurance_coordonnees = request.form.get('assurance_coordonnees')
        assurance_tel = request.form.get('assurance_tel')

        remorque_au_club = 1 if 'remorque_au_club' in request.form else 0

        # Mise à jour dans la BDD
        db.execute("""
            UPDATE bateaux SET
                nom = ?, nom_proprietaire = ?, constructeur_modele = ?, date_arrivee = ?,
                type = ?, taille = ?, couleur_coque = ?, couleur_pont = ?, annee = ?, categorie = ?,
                est_du_club = ?, remarques = ?, immatriculation = ?, numero_voile = ?,
                assurance_nom = ?, assurance_numero = ?, assurance_coordonnees = ?, assurance_tel = ?,
                remorque_au_club = ?
            WHERE id = ?
        """, (
            nom, nom_proprietaire, constructeur_modele, date_arrivee,
            type_, taille, couleur_coque, couleur_pont, annee, categorie,
            est_du_club, remarques, immatriculation, numero_voile,
            assurance_nom, assurance_numero, assurance_coordonnees, assurance_tel,
            remorque_au_club, id
        ))

        # Gestion des fichiers
        base_dir = os.path.dirname(__file__)  # ← chemin du dossier app.py
        dossier = os.path.join(base_dir, 'data', 'bateaux', str(id))
        os.makedirs(dossier, exist_ok=True)

        photo = request.files.get('photo')
        if photo and photo.filename != '':
            try:
                img = Image.open(photo)
                photo_path = os.path.join(dossier, 'photo.jpg')
                img.convert('RGB').save(photo_path, 'JPEG')
                db.execute("UPDATE bateaux SET photo = ? WHERE id = ?", (photo_path, id))
            except Exception as e:
                print("Erreur photo :", e)

        docx_file = request.files.get('docx')
        if docx_file and docx_file.filename.endswith('.docx'):
            try:
                docx_path = os.path.join(dossier, 'document.docx')
                docx_file.save(docx_path)
                db.execute("UPDATE bateaux SET docx = ? WHERE id = ?", (docx_path, id))
            except Exception as e:
                print("Erreur docx :", e)


        db.commit()
        flash("Bateau modifié avec succès.")
        ajouter_historique("bateau", f"Modification du bateau #{id}", f"Nom : {nom}", id)
        return redirect('/bateaux/liste')

    emplacements = db.execute("SELECT id, nom FROM emplacements ORDER BY nom").fetchall()
    membres = db.execute("SELECT id, nom, prenom FROM membres ORDER BY nom").fetchall()
    return render_template('bateaux/formulaire.html', bateau=bateau, emplacements=emplacements, membres=membres, modifier=True)

@app.route('/bateaux/<int:id>')
def fiche_bateau(id):
    db = get_db()
    bateau = db.execute("""
        SELECT b.*, e.nom AS emplacement
        FROM bateaux b
        LEFT JOIN emplacements e ON b.id = e.bateau_id
        WHERE b.id = ?
    """, (id,)).fetchone()

    if not bateau:
        return "Bateau introuvable", 404

    return render_template('bateaux/fiche.html', bateau=bateau)

@app.route('/bateaux/<int:bateau_id>/photo')
def photo_bateau(bateau_id):
    chemin_base = os.path.dirname(__file__)  # <-- racine réelle
    photo_path = os.path.join(chemin_base, 'data', 'bateaux', str(bateau_id), 'photo.jpg')   
    if os.path.exists(photo_path):
        return send_file(photo_path)
    return "Photo non trouvée", 404


@app.route('/bateaux/<int:bateau_id>/document')
def telecharger_docx(bateau_id):
    base = os.path.dirname(__file__)
    docx_path = os.path.join(base, 'data', 'bateaux', str(bateau_id), 'document.docx')
    if os.path.exists(docx_path):
        return send_file(docx_path, as_attachment=True)
    return "Fichier introuvable", 404

@app.route('/bateaux/supprimer/<int:id>', methods=['GET'])
def supprimer_bateau(id):
    db = get_db()

    # Vérifie que le bateau existe
    bateau = db.execute("SELECT * FROM bateaux WHERE id = ?", (id,)).fetchone()
    if not bateau:
        raise NotFound("Bateau introuvable")

    # Historique avant suppression
    nom = bateau['nom'] if bateau else f"#{id}"
    ajouter_historique("bateau", f"Suppression du bateau « {nom} »", None, id)

    # Supprimer le bateau de la base
    db.execute("DELETE FROM bateaux WHERE id = ?", (id,))
    db.commit()

    # Supprimer les fichiers associés
    base_dir = os.path.dirname(__file__)
    dossier = os.path.join(base_dir, 'data', 'bateaux', str(id))

    if os.path.exists(dossier):
        try:
            for root, dirs, files in os.walk(dossier, topdown=False):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        print(f"Erreur suppression fichier {file} :", e)
                for dir in dirs:
                    try:
                        os.rmdir(os.path.join(root, dir))
                    except Exception as e:
                        print(f"Erreur suppression sous-dossier {dir} :", e)
            os.rmdir(dossier)
        except Exception as e:
            print(f"Erreur suppression du dossier {dossier} :", e)

    flash("Bateau supprimé avec succès.")
    return redirect('/bateaux/liste')

@app.route('/paiements/port')
def paiements_port():
    db = get_db()

    # Année sélectionnée ou année en cours par défaut
    annee = int(request.args.get('annee', datetime.now().year))
    statut = request.args.get('statut', 'tous')
    recherche = request.args.get('recherche', '').lower()

    # Requête SQL modifiée pour tenir compte de la date d'arrivée
    bateaux = db.execute("""
        SELECT b.id, b.nom, b.nom_proprietaire, b.date_arrivee,
               c.est_a_jour, c.mode_paiement, c.date_paiement
        FROM bateaux b
        LEFT JOIN cotisations c ON b.id = c.bateau_id AND c.annee = ?
        WHERE b.est_du_club = 0
          AND (b.date_arrivee IS NULL OR strftime('%Y', b.date_arrivee) <= ?)
    """, (annee, str(annee))).fetchall()

    # Filtrage supplémentaire côté Python
    def filtre(b):
        match_statut = (
            (statut == 'à_jour' and b['est_a_jour'] == 1) or
            (statut == 'pas_a_jour' and (b['est_a_jour'] == 0 or b['est_a_jour'] is None)) or
            statut == 'tous'
        )
        match_recherche = recherche in (b['nom'] or '').lower() or recherche in (b['nom_proprietaire'] or '').lower()
        return match_statut and match_recherche

    bateaux_filtres = list(filter(filtre, bateaux))

    return render_template('paiements/port.html',
                           bateaux=bateaux_filtres,
                           annee=annee,
                           statut=statut,
                           recherche=recherche)

@app.route('/paiements/valider', methods=['POST'])
def valider_cotisation_avec_paiement():
    db = get_db()

    bateau_id = request.form.get('bateau_id')
    annee = request.form.get('annee')
    mode = request.form.get('mode_paiement')
    date_paiement = date.today().isoformat()

    if not all([bateau_id, annee, mode]):
        flash("Tous les champs sont requis.", "danger")
        return redirect(f"/paiements/port?annee={annee}")

    db.execute("""
        INSERT INTO cotisations (bateau_id, annee, est_a_jour, mode_paiement, date_paiement)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(bateau_id, annee) DO UPDATE SET est_a_jour = 1, mode_paiement = ?, date_paiement = ?
    """, (bateau_id, annee, mode, date_paiement, mode, date_paiement))
    db.commit()

    bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (bateau_id,)).fetchone()
    nom = bateau['nom'] if bateau else f"Bateau #{bateau_id}"
    ajouter_historique("bateau", f"Cotisation validée pour {nom} ({annee})", f"Mode : {mode}", bateau_id)

    flash("Cotisation validée avec succès.", "success")
    return redirect(f"/paiements/port?annee={annee}")

@app.route('/paiements/reinitialiser/<int:bateau_id>')
def reinitialiser_cotisation(bateau_id):
    annee = int(request.args.get('annee', 2024))
    db = get_db()

    db.execute("""
        INSERT INTO cotisations (bateau_id, annee, est_a_jour, mode_paiement, date_paiement)
        VALUES (?, ?, 0, NULL, NULL)
        ON CONFLICT(bateau_id, annee)
        DO UPDATE SET est_a_jour = 0, mode_paiement = NULL, date_paiement = NULL
    """, (bateau_id, annee))
    db.commit()

    bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (bateau_id,)).fetchone()
    nom = bateau['nom'] if bateau else f"Bateau #{bateau_id}"
    ajouter_historique("bateau", f"Réinitialisation de la cotisation de {nom} ({annee})", None, bateau_id)

    return redirect(f'/paiements/port?annee={annee}')


# GESTION EMPLACEMENTS

@app.route('/zones/liste')
def liste_zones():
    db = get_db()
    zones = db.execute("SELECT * FROM zones ORDER BY nom").fetchall()
    return render_template('zones/liste.html', zones=zones)

@app.route('/zones/ajouter', methods=['POST'])
def ajouter_zone():
    db = get_db()
    nom = request.form['nom']
    type_zone = request.form['type']
    couleur = request.form['couleur']
    nb_places = int(request.form.get('nombre_places') or 0)

    # Création de la zone
    cursor = db.execute("""
        INSERT INTO zones (nom, type, couleur, nombre_places)
        VALUES (?, ?, ?, ?)
    """, (nom, type_zone, couleur, nb_places))
    zone_id = cursor.lastrowid
    db.commit()

    # Création automatique des emplacements
    for i in range(1, nb_places + 1):
        nom_emplacement = f"{nom}-{i:02}"  # Ex: Port Est-01
        db.execute("""
            INSERT INTO emplacements (nom, zone_id, type, disponible)
            VALUES (?, ?, ?, 1)
        """, (nom_emplacement, zone_id, type_zone))

    db.commit()

    ajouter_historique("zone", f"Ajout de la zone « {nom} »", f"{nb_places} emplacements créés automatiquement", zone_id)

    return redirect('/zones/liste')

@app.route('/zones/<int:id>/emplacements')
def emplacements_zone(id):
    db = get_db()
    zone = db.execute("SELECT * FROM zones WHERE id = ?", (id,)).fetchone()
    if not zone:
        return "Zone introuvable", 404

    emplacements = db.execute("""
        SELECT e.*, b.nom AS nom_bateau
        FROM emplacements e
        LEFT JOIN bateaux b ON e.bateau_id = b.id
        WHERE e.zone_id = ?
        ORDER BY e.nom
    """, (id,)).fetchall()

    return render_template('zones/emplacements.html', zone=zone, emplacements=emplacements)

@app.route('/zones/<int:id>/emplacements/ajouter', methods=['POST'])
def ajouter_emplacement(id):
    db = get_db()
    nom = request.form['nom']
    type_ = request.form['type']
    remarque = request.form['remarque']
    
    db.execute("""
        INSERT INTO emplacements (nom, type, disponible, zone_id, remarque)
        VALUES (?, ?, 1, ?, ?)
    """, (nom, type_, id, remarque))
    db.commit()

    zone = db.execute("SELECT nom FROM zones WHERE id = ?", (id,)).fetchone()
    zone_nom = zone['nom'] if zone else f"Zone #{id}"
    ajouter_historique("zone", f"Ajout d’un emplacement « {nom} » à {zone_nom}", remarque, id)

    return redirect(f"/zones/{id}/emplacements")

@app.route('/emplacements/supprimer/<int:id>', methods=['GET', 'POST'])
def supprimer_emplacement(id):
    db = get_db()
    emplacement = db.execute("SELECT * FROM emplacements WHERE id = ?", (id,)).fetchone()

    if not emplacement:
        return "Emplacement introuvable", 404

    if request.method == 'POST':
        db.execute("DELETE FROM emplacements WHERE id = ?", (id,))
        db.commit()

        zone = db.execute("SELECT nom FROM zones WHERE id = ?", (emplacement['zone_id'],)).fetchone()
        zone_nom = zone['nom'] if zone else f"Zone #{emplacement['zone_id']}"
        ajouter_historique("zone", f"Suppression de l’emplacement « {emplacement['nom']} »", f"Zone : {zone_nom}", emplacement['zone_id'])

        return redirect(f"/zones/{emplacement['zone_id']}/emplacements")

    bateau = None
    if emplacement['bateau_id']:
        bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (emplacement['bateau_id'],)).fetchone()

    return render_template('zones/confirmer_suppression_emplacement.html', emplacement=emplacement, bateau=bateau)

@app.route('/emplacements/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_emplacement(id):
    db = get_db()
    emplacement = db.execute("SELECT * FROM emplacements WHERE id = ?", (id,)).fetchone()
    if not emplacement:
        return "Emplacement introuvable", 404

    if request.method == 'POST':
        nom = request.form['nom']
        type_ = request.form['type']
        remarque = request.form['remarque']
        disponible = 1 if 'disponible' in request.form else 0

        db.execute("""
            UPDATE emplacements
            SET nom = ?, type = ?, remarque = ?, disponible = ?
            WHERE id = ?
        """, (nom, type_, remarque, disponible, id))
        db.commit()

        zone = db.execute("SELECT nom FROM zones WHERE id = ?", (emplacement['zone_id'],)).fetchone()
        zone_nom = zone['nom'] if zone else f"Zone #{emplacement['zone_id']}"
        ajouter_historique("zone", f"Modification de l’emplacement « {nom} »", f"Zone : {zone_nom}", emplacement['zone_id'])

        return redirect(f"/zones/{emplacement['zone_id']}/emplacements")

    return render_template('zones/modifier_emplacement.html', emplacement=emplacement)

@app.route('/zones/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_zone(id):
    db = get_db()
    zone = db.execute("SELECT * FROM zones WHERE id = ?", (id,)).fetchone()
    if not zone:
        return "Zone introuvable", 404

    if request.method == 'POST':
        nom = request.form['nom']
        type_ = request.form['type']
        couleur = request.form['couleur']
        nombre_places = request.form['nombre_places']

        db.execute("""
            UPDATE zones
            SET nom = ?, type = ?, couleur = ?, nombre_places = ?
            WHERE id = ?
        """, (nom, type_, couleur, nombre_places, id))
        db.commit()

        ajouter_historique("zone", f"Modification de la zone « {nom} »", f"Type : {type_}, Couleur : {couleur}, Places : {nombre_places}", id)

        return redirect('/zones/liste')

    return render_template('zones/modifier.html', zone=zone)

@app.route('/zones/supprimer/<int:id>', methods=['GET', 'POST'])
def supprimer_zone(id):
    db = get_db()
    zone = db.execute("SELECT * FROM zones WHERE id = ?", (id,)).fetchone()

    if not zone:
        return "Zone introuvable", 404

    if request.method == 'POST':
        db.execute("DELETE FROM emplacements WHERE zone_id = ?", (id,))
        db.execute("DELETE FROM zones WHERE id = ?", (id,))
        db.commit()

        ajouter_historique("zone", f"Suppression de la zone « {zone['nom']} »", f"Tous les emplacements liés ont été supprimés", id)

        return redirect('/zones/liste')

    return render_template('zones/confirmer_suppression_zone.html', zone=zone)

@app.route('/emplacements/assigner/<int:id>', methods=['GET', 'POST'])
def assigner_bateau(id):
    db = get_db()

    e = db.execute("SELECT * FROM emplacements WHERE id = ?", (id,)).fetchone()
    if not e:
        return "Emplacement introuvable", 404

    if request.method == 'POST':
        bateau_id = request.form.get('bateau_id')
        if bateau_id:
            db.execute("""
                UPDATE emplacements
                SET bateau_id = NULL
                WHERE bateau_id = ?
            """, (bateau_id,))
            db.execute("""
                UPDATE emplacements
                SET bateau_id = ?, disponible = 0
                WHERE id = ?
            """, (bateau_id, id))
            db.commit()

            bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (bateau_id,)).fetchone()
            bateau_nom = bateau['nom'] if bateau else f"Bateau #{bateau_id}"
            ajouter_historique("zone", f"Attribution de « {bateau_nom} » à l’emplacement « {e['nom']} »", None, e['zone_id'])

        return redirect(f"/zones/{e['zone_id']}/emplacements")

    bateaux = db.execute("""
        SELECT b.id, b.nom
        FROM bateaux b
        LEFT JOIN emplacements e2 ON b.id = e2.bateau_id
        WHERE e2.id IS NULL OR e2.id = ?
        ORDER BY b.nom
    """, (id,)).fetchall()

    return render_template('zones/assigner_bateau.html', emplacement=e, bateaux=bateaux)

@app.route('/emplacements/detacher/<int:id>')
def detacher_bateau(id):
    db = get_db()
    e = db.execute("SELECT * FROM emplacements WHERE id = ?", (id,)).fetchone()
    if not e:
        return "Emplacement introuvable", 404

    bateau = None
    if e['bateau_id']:
        bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (e['bateau_id'],)).fetchone()

    db.execute("""
        UPDATE emplacements
        SET bateau_id = NULL, disponible = 1
        WHERE id = ?
    """, (id,))
    db.commit()

    bateau_nom = bateau['nom'] if bateau else "un bateau"
    ajouter_historique("zone", f"Détachement de {bateau_nom} de l’emplacement « {e['nom']} »", None, e['zone_id'])

    return redirect(f"/zones/{e['zone_id']}/emplacements")


#MEMBRES
@app.route('/membres/liste')
def liste_membres():
    db = get_db()
    statut = request.args.get('statut', 'tous')
    recherche = request.args.get('recherche', '').lower()

    # Récupération brute
    membres = db.execute("""
        SELECT * FROM membres
        ORDER BY nom, prenom
    """).fetchall()

    # Filtrage en Python
    def filtre(m):
        match_statut = (
            (statut == 'tous') or
            (statut == 'ajour' and m['cotisation_a_jour'] == 1) or
            (statut == 'pasajour' and m['cotisation_a_jour'] == 0)
        )
        match_recherche = (recherche in (m['nom'] or '').lower()) or (recherche in (m['prenom'] or '').lower())
        return match_statut and match_recherche

    membres_filtres = list(filter(filtre, membres))

    return render_template('membres/liste.html', membres=membres_filtres, statut=statut, recherche=recherche)

@app.route('/membres/ajouter', methods=['GET', 'POST'])
def ajouter_membre():
    db = get_db()
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        tel1 = request.form['tel1']
        tel2 = request.form['tel2']
        email = request.form['email']
        date_inscription = request.form.get('date_inscription') or None
        cotisation_a_jour = 1 if 'cotisation_a_jour' in request.form else 0
        mode_paiement = request.form.get('mode_paiement') or None

        cursor = db.execute("""
            INSERT INTO membres (nom, prenom, tel1, tel2, email, date_inscription, cotisation_a_jour, mode_paiement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, prenom, tel1, tel2, email, date_inscription, cotisation_a_jour, mode_paiement))
        membre_id = cursor.lastrowid
        db.commit()

        ajouter_historique("membre", f"Ajout du membre {prenom} {nom}", f"Email : {email}", membre_id)

        return redirect('/membres/liste')

    return render_template('membres/formulaire.html')

@app.route('/membres/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_membre(id):
    db = get_db()
    membre = db.execute("SELECT * FROM membres WHERE id = ?", (id,)).fetchone()
    if not membre:
        return "Membre introuvable", 404

    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        tel1 = request.form['tel1']
        tel2 = request.form['tel2']
        email = request.form['email']
        date_inscription = request.form.get('date_inscription') or None
        cotisation_a_jour = 1 if 'cotisation_a_jour' in request.form else 0
        mode_paiement = request.form.get('mode_paiement') or None

        db.execute("""
            UPDATE membres
            SET nom = ?, prenom = ?, tel1 = ?, tel2 = ?, email = ?, date_inscription = ?,
                cotisation_a_jour = ?, mode_paiement = ?
            WHERE id = ?
        """, (nom, prenom, tel1, tel2, email, date_inscription, cotisation_a_jour, mode_paiement, id))
        db.commit()

        ajouter_historique("membre", f"Modification du membre {prenom} {nom}", f"Email : {email}", id)

        return redirect('/membres/liste')

    return render_template('membres/formulaire.html', membre=membre, modifier=True)

@app.route('/membres/supprimer/<int:id>')
def supprimer_membre(id):
    db = get_db()
    
    membre = db.execute("SELECT nom, prenom FROM membres WHERE id = ?", (id,)).fetchone()

    if not membre:
        return "Membre introuvable", 404

    ajouter_historique(
        "membre",
        f"Suppression du membre {membre['prenom']} {membre['nom']}",
        None,
        id
    )

    db.execute("DELETE FROM membres WHERE id = ?", (id,))
    db.commit()
    

    return redirect('/membres/liste')

@app.route('/membres/export')
def export_membres():
    db = get_db()
    membres = db.execute("SELECT * FROM membres ORDER BY nom, prenom").fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nom","Prenom","Tel1","Tel2","Email","Cotisation","Mode paiement","Date inscription"])

    for m in membres:
        writer.writerow([
            m['nom'],
            m['prenom'],
            m['tel1'] or '',
            m['tel2'] or '',
            m['email'] or '',
            "À jour" if m['cotisation_a_jour'] else "Pas à jour",
            m['mode_paiement'] or '',
            m['date_inscription'] or ''
        ])

    ajouter_historique("membre", "Export CSV des membres", f"{len(membres)} ligne(s) exportées")

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=membres.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/membres/reinitialiser_cotisations', methods=['GET', 'POST'])
def reinitialiser_cotisations():
    db = get_db()

    # S'il s'agit d'un GET : on affiche la page de confirmation
    if request.method == 'GET':
        return render_template('membres/confirmer_reinitialiser_cotisations.html')

    # S'il s'agit d'un POST : on exécute la réinitialisation
    db.execute("UPDATE membres SET cotisation_a_jour = 0, mode_paiement = NULL")
    db.commit()
    ajouter_historique("membre", "Réinitialisation de toutes les cotisations membres", "Tous les membres sont marqués comme non à jour.")
    flash("Toutes les cotisations ont été réinitialisées (personne n'est plus à jour).", "warning")

    return redirect('/membres/liste')


#LOCATIONS
@app.route('/locations/liste')
def liste_locations():
    db = get_db()

    # Locations EN COURS
    locations_encours = db.execute("""
        SELECT l.id AS location_id,
               b.id AS bateau_id, b.nom AS nom_bateau, b.indisponible,
               m.id AS membre_id, m.nom AS nom_membre, m.prenom AS prenom_membre,
               l.debut, l.fin
        FROM locations l
        JOIN bateaux b ON l.bateau_id = b.id
        JOIN membres m ON l.membre_id = m.id
        WHERE l.annule = 0
          AND REPLACE(l.fin, 'T', ' ') >= datetime('now')
        ORDER BY l.debut ASC
    """).fetchall()

    # Bateaux du club
    bateaux = db.execute("""
        SELECT b.id, b.nom, b.constructeur_modele, b.indisponible,
               (
                 SELECT l.id
                 FROM locations l
                 WHERE l.bateau_id = b.id
                   AND l.annule = 0
                   AND REPLACE(l.fin, 'T', ' ') >= datetime('now')
                 LIMIT 1
               ) AS location_id
        FROM bateaux b
        WHERE b.est_du_club = 1
        ORDER BY b.nom
    """).fetchall()

    return render_template(
        'locations/liste_double.html',
        locations_encours=locations_encours,
        bateaux=bateaux
    )

@app.route('/locations/<int:id>')
def fiche_location(id):
    db = get_db()

    location = db.execute("""
        SELECT l.*, 
               b.nom AS nom_bateau, b.constructeur_modele, b.docx,
               m.nom AS nom_membre, m.prenom AS prenom_membre
        FROM locations l
        JOIN bateaux b ON l.bateau_id = b.id
        JOIN membres m ON l.membre_id = m.id
        WHERE l.id = ?
    """, (id,)).fetchone()

    if not location:
        return "Location introuvable", 404

    return render_template('locations/fiche.html', location=location)

@app.route('/locations/ajouter', methods=['GET','POST'])
def ajouter_location():
    db = get_db()
    bateau_id = request.args.get('bateau_id')

    if request.method == 'POST':
        bateau_id = request.form['bateau_id']
        membre_id = request.form['membre_id']
        debut = request.form['debut']  # ex: "2025-04-23 15:00"
        fin = request.form['fin']

        # Insertion de la location
        db.execute("""
            INSERT INTO locations (bateau_id, membre_id, debut, fin)
            VALUES (?, ?, ?, ?)
        """, (bateau_id, membre_id, debut, fin))
        db.commit()

        # Historique
        bateau = db.execute("SELECT nom FROM bateaux WHERE id = ?", (bateau_id,)).fetchone()
        membre = db.execute("SELECT nom, prenom FROM membres WHERE id = ?", (membre_id,)).fetchone()
        bateau_nom = bateau['nom'] if bateau else f"Bateau #{bateau_id}"
        membre_nom = f"{membre['prenom']} {membre['nom']}" if membre else f"Membre #{membre_id}"

        ajouter_historique(
            "location",
            f"Location du bateau « {bateau_nom} »",
            f"Par {membre_nom}, de {debut} à {fin}",
            bateau_id
        )

        return redirect('/locations/liste')

    # Préparation du formulaire
    bateau = db.execute("SELECT * FROM bateaux WHERE id = ?", (bateau_id,)).fetchone()
    membres = db.execute("SELECT * FROM membres ORDER BY nom, prenom").fetchall()
    return render_template('locations/formulaire.html', bateau=bateau, membres=membres)


@app.route('/statistiques/locations')
def stats_locations():
    db = get_db()
    stats = db.execute("""
        SELECT b.nom AS bateau,
               COUNT(l.id) AS nb_locations,
               SUM(
                  (JULIANDAY(l.fin) - JULIANDAY(l.debut)) * 24
               ) AS total_heures
        FROM bateaux b
        LEFT JOIN locations l ON b.id = l.bateau_id
        WHERE b.est_du_club = 1 AND l.annule = 0
        GROUP BY b.id
        ORDER BY total_heures DESC
    """).fetchall()
    return render_template('statistiques/locations.html', stats=stats)

@app.route('/locations/toggle_dispo/<int:id>', methods=['POST'])
def toggle_dispo_bateau(id):
    db = get_db()
    bateau = db.execute("SELECT indisponible FROM bateaux WHERE id = ?", (id,)).fetchone()
    if not bateau:
        return "Bateau introuvable", 404

    # Basculer la valeur
    new_value = 0 if bateau['indisponible'] else 1
    db.execute("UPDATE bateaux SET indisponible = ? WHERE id = ?", (new_value, id))
    db.commit()

    # On revient à la liste
    return redirect('/locations/liste')

@app.route('/locations/annuler/<int:id>', methods=['POST'])
def annuler_location(id):
    db = get_db()
    location = db.execute("""
        SELECT l.id, l.debut, l.fin, b.nom AS bateau, m.prenom, m.nom AS nom_membre
        FROM locations l
        LEFT JOIN bateaux b ON l.bateau_id = b.id
        LEFT JOIN membres m ON l.membre_id = m.id
        WHERE l.id = ?
    """, (id,)).fetchone()

    if not location:
        return "Location introuvable", 404

    db.execute("UPDATE locations SET annule = 1 WHERE id = ?", (id,))
    db.commit()

    bateau_nom = location['bateau'] or f"Bateau ?"
    membre_nom = f"{location['prenom']} {location['nom_membre']}" if location['prenom'] else "Membre inconnu"
    ajouter_historique("location", f"Annulation location bateau « {bateau_nom} »", f"Par {membre_nom}, de {location['debut']} à {location['fin']}", id)

    flash("La location a été annulée.", "warning")
    return redirect('/locations/liste')

@app.route('/locations/historique')
def historique_locations():
    db = get_db()
    locations = db.execute("""
        SELECT l.id AS location_id,
               b.nom AS nom_bateau,
               m.nom AS nom_membre, m.prenom AS prenom_membre,
               l.debut, l.fin, l.annule
        FROM locations l
        JOIN bateaux b ON l.bateau_id = b.id
        JOIN membres m ON l.membre_id = m.id
        WHERE l.annule = 0
          AND l.fin < datetime('now')
        ORDER BY l.fin DESC
    """).fetchall()

    return render_template('locations/historique.html', locations=locations)


#MAINTENANCE
@app.route('/maintenance/liste')
def liste_maintenances():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()
    statut = request.args.get('statut', 'tous')
    page = int(request.args.get('page', 1))
    par_page = 20
    offset = (page - 1) * par_page

    query = """
        SELECT m.*, b.nom AS nom_bateau
        FROM maintenances m
        LEFT JOIN bateaux b ON m.bateau_id = b.id
        WHERE 1=1
    """
    params = []

    if recherche:
        query += " AND (m.titre LIKE ? OR m.categorie LIKE ? OR m.description LIKE ?)"
        like = f"%{recherche}%"
        params.extend([like, like, like])

    if statut != "tous":
        query += " AND m.statut = ?"
        params.append(statut)

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total = db.execute(count_query, params).fetchone()[0]

    query += " ORDER BY m.date_creation DESC LIMIT ? OFFSET ?"
    params.extend([par_page, offset])

    maintenances = db.execute(query, params).fetchall()
    nb_pages = (total + par_page - 1) // par_page

    return render_template("maintenance/liste.html",
                           maintenances=maintenances,
                           recherche=recherche,
                           statut=statut,
                           page=page,
                           nb_pages=nb_pages)

@app.route('/maintenance/<int:id>')
def fiche_maintenance(id):
    db = get_db()

    maintenance = db.execute("""
        SELECT m.*, b.nom AS nom_bateau
        FROM maintenances m
        LEFT JOIN bateaux b ON m.bateau_id = b.id
        WHERE m.id = ?
    """, (id,)).fetchone()

    if not maintenance:
        return "Maintenance introuvable", 404

    taches = db.execute("""
        SELECT t.*, m.nom AS nom_membre
        FROM taches t
        LEFT JOIN membres m ON t.membre_id = m.id
        WHERE t.maintenance_id = ?
    """, (id,)).fetchall()

    pieces = db.execute("""
        SELECT p.*, f.nom AS fournisseur
        FROM pieces p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.maintenance_id = ?
    """, (id,)).fetchall()

    documents = db.execute("SELECT * FROM documents WHERE maintenance_id = ?", (id,)).fetchall()
    photos = db.execute("SELECT * FROM photos WHERE maintenance_id = ?", (id,)).fetchall()
    commentaires = db.execute("SELECT * FROM commentaires WHERE maintenance_id = ? ORDER BY date DESC", (id,)).fetchall()

    # Tags liés à cette maintenance
    tags = db.execute("""
        SELECT t.nom
        FROM maintenance_tags mt
        JOIN tags t ON mt.tag_id = t.id
        WHERE mt.maintenance_id = ?
    """, (id,)).fetchall()

    tags_ids = [row['tag_id'] for row in db.execute("SELECT tag_id FROM maintenance_tags WHERE maintenance_id = ?", (id,))]
    tous_les_tags = db.execute("SELECT id, nom FROM tags ORDER BY nom").fetchall()

    membres = db.execute("SELECT id, nom, prenom FROM membres ORDER BY nom").fetchall()
    fournisseurs = db.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()

    categories = [
        "Port", "Quai", "Ponton", "Anneau", "Borne électrique", "Tuyau d’eau", "Rampe",
        "Zone stockage", "Atelier", "Vestiaire", "Clé", "Toiture", "Sécurité",
        "Entretien courant", "Nettoyage", "Hivernage", "Gréement", "Cordage",
        "Voile", "Mât", "Gouvernail", "Bôme", "Dérive", "Accastillage", "Coque",
        "Gilet", "Matériel sécurité", "Remorque", "Treuil", "Tirant", "Bateau école",
        "Plancher", "Serrure", "Alimentation", "Signalétique", "Électricité",
        "Moteur", "Équipement électronique", "Plomberie", "Autre"
    ]

    return render_template("maintenance/fiche.html",
        maintenance=maintenance,
        taches=taches,
        pieces=pieces,
        documents=documents,
        photos=photos,
        commentaires=commentaires,
        tags=tags,
        tags_ids=tags_ids,
        tous_les_tags=tous_les_tags,
        membres=membres,
        fournisseurs=fournisseurs,
        categories=categories
    )

@app.route('/maintenance/<int:id>/tags/modifier', methods=['POST'])
def modifier_tags_maintenance(id):
    db = get_db()

    # Supprime tous les tags existants pour cette maintenance
    db.execute("DELETE FROM maintenance_tags WHERE maintenance_id = ?", (id,))

    # Récupère les nouveaux tags cochés dans le formulaire
    tag_ids = request.form.getlist('tags')

    for tag_id in tag_ids:
        db.execute(
            "INSERT INTO maintenance_tags (maintenance_id, tag_id) VALUES (?, ?)",
            (id, tag_id)
        )

    db.commit()
    flash("Tags mis à jour.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/ajouter', methods=['GET', 'POST'])
def ajouter_maintenance():
    db = get_db()

    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form['description']
        statut = request.form['statut']
        priorite = request.form['priorite']
        categorie = request.form['categorie']
        bateau_id = request.form.get('bateau_id') or None
        tag_ids = request.form.getlist('tags')

        cursor = db.execute("""
            INSERT INTO maintenances (titre, description, statut, priorite, categorie, bateau_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (titre, description, statut, priorite, categorie, bateau_id))
        maintenance_id = cursor.lastrowid
        db.commit()
        ajouter_historique("maintenance", f"Création maintenance « {titre} »", description, maintenance_id)

        # Lier les tags
        for tag_id in tag_ids:
            db.execute("""
                INSERT INTO maintenance_tags (maintenance_id, tag_id)
                VALUES (?, ?)
            """, (maintenance_id, tag_id))

        db.commit()
        flash("Maintenance ajoutée avec succès.", "success")
        return redirect(f"/maintenance/{maintenance_id}")

    # GET : charger les choix de bateau et tags
    bateaux = db.execute("""
    SELECT id, nom FROM bateaux
    WHERE est_du_club = 1
    ORDER BY nom
    """).fetchall()
    tags = db.execute("SELECT id, nom FROM tags ORDER BY nom").fetchall()
    categories = [
    "Port", "Quai", "Ponton", "Anneau", "Borne électrique", "Tuyau d’eau", "Rampe",
    "Zone stockage", "Atelier", "Vestiaire", "Clé", "Toiture", "Sécurité",
    "Entretien courant", "Nettoyage", "Hivernage", "Gréement", "Cordage",
    "Voile", "Mât", "Gouvernail", "Bôme", "Dérive", "Accastillage", "Coque",
    "Gilet", "Matériel sécurité", "Remorque", "Treuil", "Tirant", "Bateau école",
    "Plancher", "Serrure", "Alimentation", "Signalétique", "Électricité",
    "Moteur", "Équipement électronique", "Plomberie", "Autre"
    ]

    return render_template('maintenance/formulaire.html', bateaux=bateaux, tags=tags, categories=categories)

@app.route('/maintenance/<int:id>/taches/ajouter', methods=['POST'])
def ajouter_tache(id):
    db = get_db()
    description = request.form['description']
    statut = request.form['statut']
    membre_id = request.form.get('membre_id') or None
    fournisseur_id = request.form.get('fournisseur_id') or None

    db.execute("""
        INSERT INTO taches (maintenance_id, description, statut, membre_id, fournisseur_id)
        VALUES (?, ?, ?, ?, ?)
    """, (id, description, statut, membre_id, fournisseur_id))
    db.commit()

    auteur = ""
    if membre_id:
        membre = db.execute("SELECT nom, prenom FROM membres WHERE id = ?", (membre_id,)).fetchone()
        if membre:
            auteur = f" (assignée à {membre['prenom']} {membre['nom']})"

    ajouter_historique("maintenance", f"Ajout d’une tâche à la maintenance #{id}", description + auteur, id)

    flash("Tâche ajoutée avec succès.", "success")
    return redirect(f'/maintenance/{id}')

@app.route('/maintenance/taches/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_tache(id):
    db = get_db()
    tache = db.execute("SELECT * FROM taches WHERE id = ?", (id,)).fetchone()
    if not tache:
        return "Tâche introuvable", 404

    if request.method == 'POST':
        description = request.form['description']
        statut = request.form['statut']
        membre_id = request.form.get('membre_id') or None
        fournisseur_id = request.form.get('fournisseur_id') or None

        db.execute("""
            UPDATE taches
            SET description = ?, statut = ?, membre_id = ?, fournisseur_id = ?
            WHERE id = ?
        """, (description, statut, membre_id, fournisseur_id, id))
        db.commit()

        membre = db.execute("SELECT nom, prenom FROM membres WHERE id = ?", (membre_id,)).fetchone() if membre_id else None
        nom_membre = f" (assignée à {membre['prenom']} {membre['nom']})" if membre else ""
        ajouter_historique("maintenance", f"Modification d’une tâche #{id}", description + nom_membre, tache['maintenance_id'])

        flash("Tâche modifiée.", "success")
        return redirect(f"/maintenance/{tache['maintenance_id']}")

    membres = db.execute("SELECT id, nom, prenom FROM membres ORDER BY nom").fetchall()
    fournisseurs = db.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()

    return render_template("maintenance/modifier_tache.html", tache=tache, membres=membres, fournisseurs=fournisseurs)

@app.route('/maintenance/taches/supprimer/<int:id>', methods=['POST'])
def supprimer_tache(id):
    db = get_db()
    tache = db.execute("SELECT id, maintenance_id, description FROM taches WHERE id = ?", (id,)).fetchone()
    if not tache:
        return "Tâche introuvable", 404

    db.execute("DELETE FROM taches WHERE id = ?", (id,))
    db.commit()

    ajouter_historique("maintenance", f"Suppression d’une tâche de la maintenance #{tache['maintenance_id']}", tache['description'], tache['maintenance_id'])

    flash("Tâche supprimée.", "warning")
    return redirect(f"/maintenance/{tache['maintenance_id']}")

@app.route('/maintenance/<int:id>/pieces/ajouter', methods=['POST'])
def ajouter_piece(id):
    db = get_db()
    nom = request.form['nom']
    quantite = request.form.get('quantite') or 1
    statut = request.form['statut']
    fournisseur_id = request.form.get('fournisseur_id') or None

    db.execute("""
        INSERT INTO pieces (maintenance_id, nom, quantite, statut_commande, fournisseur_id)
        VALUES (?, ?, ?, ?, ?)
    """, (id, nom, quantite, statut, fournisseur_id))
    db.commit()

    fournisseur = db.execute("SELECT nom FROM fournisseurs WHERE id = ?", (fournisseur_id,)).fetchone() if fournisseur_id else None
    commentaire = f"{quantite} × {nom} — Statut : {statut}"
    if fournisseur:
        commentaire += f" — Fournisseur : {fournisseur['nom']}"

    ajouter_historique("maintenance", f"Ajout de pièce à la maintenance #{id}", commentaire, id)

    flash("Pièce ajoutée.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/pieces/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_piece(id):
    db = get_db()
    piece = db.execute("SELECT * FROM pieces WHERE id = ?", (id,)).fetchone()
    if not piece:
        return "Pièce introuvable", 404

    if request.method == 'POST':
        nom = request.form['nom']
        quantite = request.form.get('quantite') or 1
        statut = request.form['statut']
        fournisseur_id = request.form.get('fournisseur_id') or None

        db.execute("""
            UPDATE pieces
            SET nom = ?, quantite = ?, statut_commande = ?, fournisseur_id = ?
            WHERE id = ?
        """, (nom, quantite, statut, fournisseur_id, id))
        db.commit()

        fournisseur = db.execute("SELECT nom FROM fournisseurs WHERE id = ?", (fournisseur_id,)).fetchone() if fournisseur_id else None
        commentaire = f"{quantite} × {nom} — Statut : {statut}"
        if fournisseur:
            commentaire += f" — Fournisseur : {fournisseur['nom']}"

        ajouter_historique("maintenance", f"Modification de pièce #{id} (maintenance #{piece['maintenance_id']})", commentaire, piece['maintenance_id'])

        flash("Pièce modifiée.", "success")
        return redirect(f"/maintenance/{piece['maintenance_id']}")

    fournisseurs = db.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
    return render_template("maintenance/modifier_piece.html", piece=piece, fournisseurs=fournisseurs)

@app.route('/maintenance/pieces/supprimer/<int:id>', methods=['POST'])
def supprimer_piece(id):
    db = get_db()
    piece = db.execute("SELECT id, maintenance_id, nom, quantite FROM pieces WHERE id = ?", (id,)).fetchone()
    if not piece:
        return "Pièce introuvable", 404

    db.execute("DELETE FROM pieces WHERE id = ?", (id,))
    db.commit()

    commentaire = f"{piece['quantite']} × {piece['nom']}"
    ajouter_historique("maintenance", f"Suppression de pièce (maintenance #{piece['maintenance_id']})", commentaire, piece['maintenance_id'])

    flash("Pièce supprimée.", "warning")
    return redirect(f"/maintenance/{piece['maintenance_id']}")

@app.route('/maintenance/<int:id>/modifier_statut', methods=['POST'])
def modifier_statut_maintenance(id):
    db = get_db()
    statut = request.form['statut']

    db.execute("UPDATE maintenances SET statut = ? WHERE id = ?", (statut, id))
    db.commit()

    ajouter_historique("maintenance", f"Modification du statut de la maintenance #{id}", f"Nouveau statut : {statut}", id)

    flash("Statut mis à jour.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/<int:id>/modifier_priorite', methods=['POST'])
def modifier_priorite_maintenance(id):
    db = get_db()
    priorite = request.form['priorite']

    db.execute("UPDATE maintenances SET priorite = ? WHERE id = ?", (priorite, id))
    db.commit()

    ajouter_historique("maintenance", f"Modification de la priorité (maintenance #{id})", f"Nouvelle priorité : {priorite}", id)

    flash("Priorité mise à jour.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/<int:id>/modifier_description', methods=['POST'])
def modifier_description_maintenance(id):
    db = get_db()
    description = request.form['description']

    db.execute("UPDATE maintenances SET description = ? WHERE id = ?", (description, id))
    db.commit()

    ajouter_historique("maintenance", f"Modification de la description (maintenance #{id})", description, id)

    flash("Description mise à jour.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/<int:id>/documents/ajouter', methods=['POST'])
def ajouter_document(id):
    db = get_db()
    fichier = request.files.get('fichier')
    if not fichier or fichier.filename == '':
        flash("Aucun fichier sélectionné.", "warning")
        return redirect(f"/maintenance/{id}")

    # Utiliser un chemin absolu basé sur l’emplacement de app.py
    base_dir = os.path.dirname(__file__)
    dossier = os.path.join(base_dir, "data", "maintenances", str(id), "documents")
    os.makedirs(dossier, exist_ok=True)

    # Enregistrement sécurisé du fichier
    nom_fichier = secure_filename(fichier.filename)
    chemin = os.path.join(dossier, nom_fichier)
    fichier.save(chemin)

    # Enregistrement en BDD
    db.execute("""
        INSERT INTO documents (maintenance_id, nom, type, chemin)
        VALUES (?, ?, ?, ?)
    """, (id, nom_fichier, fichier.mimetype, chemin))
    db.commit()

    # Historique
    ajouter_historique("maintenance", f"Ajout de document à la maintenance #{id}", nom_fichier, id)

    flash("Document ajouté.", "success")
    return redirect(f"/maintenance/{id}")

from flask import abort

@app.route('/maintenance/photos/supprimer/<int:id>', methods=['POST'])
def supprimer_photo(id):
    db = get_db()
    photo = db.execute("SELECT id, maintenance_id, chemin FROM photos WHERE id = ?", (id,)).fetchone()
    if not photo:
        return "Photo introuvable", 404

    # Assure que le chemin est absolu
    chemin_photo = photo['chemin']
    if not os.path.isabs(chemin_photo):
        chemin_photo = os.path.join(os.path.dirname(__file__), chemin_photo)

    # Supprimer le fichier du disque
    try:
        if os.path.exists(chemin_photo):
            os.remove(chemin_photo)
    except Exception as e:
        print("Erreur suppression fichier :", e)

    # Supprimer en base
    db.execute("DELETE FROM photos WHERE id = ?", (id,))
    db.commit()

    ajouter_historique("maintenance", f"Suppression d'une photo (maintenance #{photo['maintenance_id']})", chemin_photo, photo['maintenance_id'])

    flash("Photo supprimée.", "warning")
    return redirect(f"/maintenance/{photo['maintenance_id']}")


@app.route('/maintenance/documents/supprimer/<int:id>', methods=['POST'])
def supprimer_document(id):
    db = get_db()
    document = db.execute("SELECT id, maintenance_id, chemin, nom FROM documents WHERE id = ?", (id,)).fetchone()
    if not document:
        return "Document introuvable", 404

    chemin_document = document['chemin']
    if not os.path.isabs(chemin_document):
        chemin_document = os.path.join(os.path.dirname(__file__), chemin_document)

    try:
        if os.path.exists(chemin_document):
            os.remove(chemin_document)
    except Exception as e:
        print("Erreur lors de la suppression du fichier :", e)

    db.execute("DELETE FROM documents WHERE id = ?", (id,))
    db.commit()

    ajouter_historique("maintenance", f"Suppression d'un document (maintenance #{document['maintenance_id']})", document['nom'], document['maintenance_id'])

    flash("Document supprimé.", "warning")
    return redirect(f"/maintenance/{document['maintenance_id']}")


@app.route('/maintenance/<int:id>/photos/ajouter', methods=['POST'])
def ajouter_photo(id):
    db = get_db()
    fichier = request.files.get('photo')
    commentaire = request.form.get('commentaire') or ''

    if not fichier or fichier.filename == '':
        flash("Aucune photo sélectionnée.", "warning")
        return redirect(f"/maintenance/{id}")

    base_dir = os.path.dirname(__file__)
    dossier = os.path.join(base_dir, "data", "maintenances", str(id), "photos")
    os.makedirs(dossier, exist_ok=True)

    nom_fichier = secure_filename(fichier.filename)
    nom_final = os.path.splitext(nom_fichier)[0] + ".jpg"
    chemin_final = os.path.join(dossier, nom_final)

    try:
        image = Image.open(fichier)
        image.convert("RGB").save(chemin_final, "JPEG")
    except Exception as e:
        flash("Erreur lors de l'enregistrement de la photo.", "danger")
        print(e)
        return redirect(f"/maintenance/{id}")

    db.execute("""
        INSERT INTO photos (maintenance_id, chemin, commentaire)
        VALUES (?, ?, ?)
    """, (id, chemin_final, commentaire))
    db.commit()

    ajouter_historique("maintenance", f"Ajout d'une photo à la maintenance #{id}", commentaire, id)

    flash("Photo ajoutée.", "success")
    return redirect(f"/maintenance/{id}")


@app.route('/maintenance/documents/voir/<int:id>')
def voir_document(id):
    db = get_db()
    doc = db.execute("SELECT chemin, nom FROM documents WHERE id = ?", (id,)).fetchone()
    if not doc:
        return "Document introuvable", 404

    return send_file(doc['chemin'], as_attachment=False, download_name=doc['nom'])

@app.route('/maintenance/photos/voir/<int:id>')
def voir_photo(id):
    db = get_db()
    photo = db.execute("SELECT chemin FROM photos WHERE id = ?", (id,)).fetchone()
    if not photo:
        return "Photo introuvable", 404

    return send_file(photo['chemin'], mimetype='image/jpeg')

@app.route('/maintenance/<int:id>/commentaires/ajouter', methods=['POST'])
def ajouter_commentaire(id):
    db = get_db()
    texte = request.form['texte']
    auteur = request.form.get('auteur') or '—'

    db.execute("""
        INSERT INTO commentaires (maintenance_id, texte, auteur)
        VALUES (?, ?, ?)
    """, (id, texte, auteur))
    db.commit()

    ajouter_historique("maintenance", f"Ajout d’un commentaire (maintenance #{id})", f"{auteur} : {texte}", id)

    flash("Commentaire ajouté.", "success")
    return redirect(f"/maintenance/{id}")

@app.route('/maintenance/commentaires/supprimer/<int:id>', methods=['POST'])
def supprimer_commentaire(id):
    db = get_db()
    commentaire = db.execute("SELECT id, maintenance_id, auteur, texte FROM commentaires WHERE id = ?", (id,)).fetchone()
    if not commentaire:
        return "Commentaire introuvable", 404

    db.execute("DELETE FROM commentaires WHERE id = ?", (id,))
    db.commit()

    contenu = f"{commentaire['auteur']} : {commentaire['texte']}"
    ajouter_historique("maintenance", f"Suppression d’un commentaire (maintenance #{commentaire['maintenance_id']})", contenu, commentaire['maintenance_id'])

    flash("Commentaire supprimé.", "warning")
    return redirect(f"/maintenance/{commentaire['maintenance_id']}")

@app.route('/maintenance/<int:id>/modifier_categorie', methods=['POST'])
def modifier_categorie_maintenance(id):
    db = get_db()
    nouvelle_categorie = request.form['categorie']

    db.execute("UPDATE maintenances SET categorie = ? WHERE id = ?", (nouvelle_categorie, id))
    db.commit()

    ajouter_historique("maintenance", f"Modification de la catégorie (maintenance #{id})", f"Nouvelle catégorie : {nouvelle_categorie}", id)

    flash("Catégorie mise à jour.", "success")
    return redirect(f"/maintenance/{id}")


@app.route('/maintenance/export_csv')
def export_csv_maintenances():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()
    statut = request.args.get('statut', 'tous')

    query = """
        SELECT DISTINCT m.id, m.titre, m.date_creation, m.statut, m.priorite, m.categorie,
               b.nom AS nom_bateau
        FROM maintenances m
        LEFT JOIN bateaux b ON m.bateau_id = b.id
        LEFT JOIN commentaires c ON c.maintenance_id = m.id
        LEFT JOIN maintenance_tags mt ON mt.maintenance_id = m.id
        LEFT JOIN tags t ON t.id = mt.tag_id
        WHERE 1=1
    """
    params = []

    if recherche:
        query += """
            AND (
                m.titre LIKE ?
                OR m.description LIKE ?
                OR m.categorie LIKE ?
                OR c.texte LIKE ?
                OR t.nom LIKE ?
            )
        """
        for _ in range(5):
            params.append(f"%{recherche}%")

    if statut != 'tous':
        query += " AND m.statut = ?"
        params.append(statut)

    query += " ORDER BY m.date_creation DESC"

    maintenances = db.execute(query, params).fetchall()

    # Création de la réponse CSV
    def generate_csv():
        yield "ID,Titre,Bateau,Catégorie,Statut,Priorité,Date création\n"
        for m in maintenances:
            ligne = f"{m['id']},{m['titre']},{m['nom_bateau'] or ''},{m['categorie'] or ''},{m['statut']},{m['priorite']},{m['date_creation'][:10]}\n"
            yield ligne

    return Response(generate_csv(), mimetype='text/csv', headers={
        "Content-Disposition": "attachment; filename=maintenances.csv"
    })

@app.route('/maintenance/bateau/<int:id>')
def maintenances_par_bateau(id):
    db = get_db()
    recherche = request.args.get('recherche', '').strip()
    statut = request.args.get('statut', 'tous')

    # Récupérer les infos du bateau
    bateau = db.execute("SELECT id, nom FROM bateaux WHERE id = ?", (id,)).fetchone()
    if not bateau:
        return "Bateau introuvable", 404

    query = """
        SELECT DISTINCT m.id, m.titre, m.date_creation, m.statut, m.priorite, m.categorie,
               b.nom AS nom_bateau
        FROM maintenances m
        LEFT JOIN bateaux b ON m.bateau_id = b.id
        LEFT JOIN commentaires c ON c.maintenance_id = m.id
        LEFT JOIN maintenance_tags mt ON mt.maintenance_id = m.id
        LEFT JOIN tags t ON t.id = mt.tag_id
        WHERE m.bateau_id = ?
    """
    params = [id]

    if recherche:
        query += """
            AND (
                m.titre LIKE ?
                OR m.description LIKE ?
                OR m.categorie LIKE ?
                OR c.texte LIKE ?
                OR t.nom LIKE ?
            )
        """
        for _ in range(5):
            params.append(f"%{recherche}%")

    if statut != 'tous':
        query += " AND m.statut = ?"
        params.append(statut)

    query += " ORDER BY m.date_creation DESC"

    maintenances = db.execute(query, params).fetchall()

    return render_template("maintenance/liste.html",
        maintenances=maintenances,
        recherche=recherche,
        statut=statut,
        bateau=bateau
    )

#FOURNISSEUR
@app.route('/fournisseurs/liste')
def liste_fournisseurs():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()

    if recherche:
        fournisseurs = db.execute("""
            SELECT * FROM fournisseurs
            WHERE nom LIKE ? OR contact LIKE ? OR email LIKE ?
            ORDER BY nom
        """, (f"%{recherche}%", f"%{recherche}%", f"%{recherche}%")).fetchall()
    else:
        fournisseurs = db.execute("SELECT * FROM fournisseurs ORDER BY nom").fetchall()

    return render_template("fournisseurs/liste.html", fournisseurs=fournisseurs, recherche=recherche)

@app.route('/fournisseurs/ajouter', methods=['GET', 'POST'])
def ajouter_fournisseur():
    db = get_db()
    
    if request.method == 'POST':
        nom = request.form['nom']
        siret = request.form.get('siret')
        site_web = request.form.get('site_web')
        contact = request.form.get('contact')
        email = request.form.get('email')
        telephone = request.form.get('telephone')

        cursor = db.execute("""
            INSERT INTO fournisseurs (nom, siret, site_web, contact, email, telephone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nom, siret, site_web, contact, email, telephone))
        fournisseur_id = cursor.lastrowid
        db.commit()

        ajouter_historique("fournisseur", f"Ajout du fournisseur « {nom} »", f"Contact : {contact}, Email : {email}", fournisseur_id)

        flash("Fournisseur ajouté avec succès.", "success")
        return redirect('/fournisseurs/liste')

    return render_template('fournisseurs/formulaire.html')

@app.route('/fournisseurs/<int:id>')
def fiche_fournisseur(id):
    db = get_db()

    fournisseur = db.execute("""
        SELECT * FROM fournisseurs WHERE id = ?
    """, (id,)).fetchone()

    if not fournisseur:
        return "Fournisseur introuvable", 404

    pieces = db.execute("""
        SELECT p.nom, p.quantite, p.statut_commande, p.maintenance_id,
               m.titre AS titre_maintenance, m.date_creation
        FROM pieces p
        JOIN maintenances m ON m.id = p.maintenance_id
        WHERE p.fournisseur_id = ?
        ORDER BY m.date_creation DESC
    """, (id,)).fetchall()

    return render_template("fournisseurs/fiche.html",
        fournisseur=fournisseur,
        pieces=pieces
    )

@app.route('/fournisseurs/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_fournisseur(id):
    db = get_db()
    fournisseur = db.execute("SELECT * FROM fournisseurs WHERE id = ?", (id,)).fetchone()
    if not fournisseur:
        return "Fournisseur introuvable", 404

    if request.method == 'POST':
        nom = request.form['nom']
        siret = request.form.get('siret')
        site_web = request.form.get('site_web')
        contact = request.form.get('contact')
        email = request.form.get('email')
        telephone = request.form.get('telephone')

        db.execute("""
            UPDATE fournisseurs
            SET nom = ?, siret = ?, site_web = ?, contact = ?, email = ?, telephone = ?
            WHERE id = ?
        """, (nom, siret, site_web, contact, email, telephone, id))
        db.commit()

        ajouter_historique("fournisseur", f"Modification du fournisseur « {nom} »", f"Contact : {contact}, Email : {email}", id)

        flash("Fournisseur mis à jour.", "success")
        return redirect(f"/fournisseurs/{id}")

    return render_template('fournisseurs/formulaire.html', fournisseur=fournisseur)

@app.route('/fournisseurs/supprimer/<int:id>', methods=['POST'])
def supprimer_fournisseur(id):
    db = get_db()

    lien_pieces = db.execute("SELECT COUNT(*) AS total FROM pieces WHERE fournisseur_id = ?", (id,)).fetchone()["total"]
    lien_taches = db.execute("SELECT COUNT(*) AS total FROM taches WHERE fournisseur_id = ?", (id,)).fetchone()["total"]

    if lien_pieces > 0 or lien_taches > 0:
        flash("Impossible de supprimer ce fournisseur : il est lié à une ou plusieurs pièces ou tâches.", "danger")
        return redirect(f"/fournisseurs/{id}")

    fournisseur = db.execute("SELECT nom FROM fournisseurs WHERE id = ?", (id,)).fetchone()
    nom = fournisseur['nom'] if fournisseur else f"Fournisseur #{id}"

    db.execute("DELETE FROM fournisseurs WHERE id = ?", (id,))
    db.commit()

    ajouter_historique("fournisseur", f"Suppression du fournisseur « {nom} »", None, id)

    flash("Fournisseur supprimé.", "warning")
    return redirect("/fournisseurs/liste")

@app.route('/fournisseurs/export_csv')
def export_csv_fournisseurs():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()

    if recherche:
        fournisseurs = db.execute("""
            SELECT * FROM fournisseurs
            WHERE nom LIKE ? OR contact LIKE ? OR email LIKE ?
            ORDER BY nom
        """, (f"%{recherche}%", f"%{recherche}%", f"%{recherche}%")).fetchall()
    else:
        fournisseurs = db.execute("SELECT * FROM fournisseurs ORDER BY nom").fetchall()

    def generate_csv():
        yield "Nom,SIRET,Site web,Contact,Email,Téléphone\n"
        for f in fournisseurs:
            yield f"{f['nom']},{f['siret'] or ''},{f['site_web'] or ''},{f['contact'] or ''},{f['email'] or ''},{f['telephone'] or ''}\n"

    return Response(generate_csv(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=fournisseurs.csv"
    })

# PLANNING / Agenda 
@app.route('/agenda/planning')
def planning():
    db = get_db()
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')

    query = "SELECT * FROM agenda WHERE 1=1"
    params = []

    if date_min:
        query += " AND date >= ?"
        params.append(date_min)
    if date_max:
        query += " AND date <= ?"
        params.append(date_max)

    query += " ORDER BY date DESC, heure_debut DESC"

    evenements = db.execute(query, params).fetchall()

    return render_template('agenda/planning.html',
                           evenements=evenements,
                           date_min=date_min,
                           date_max=date_max)

@app.route('/agenda/ajouter', methods=['GET', 'POST'])
def ajouter_evenement():
    db = get_db()

    if request.method == 'POST':
        titre = request.form['titre']
        date = request.form['date']
        heure_debut = request.form.get('heure_debut') or None
        heure_fin = request.form.get('heure_fin') or None
        commentaire = request.form.get('annotation') or None

        db.execute("""
            INSERT INTO agenda (titre, date, heure_debut, heure_fin, annotation)
            VALUES (?, ?, ?, ?, ?)
        """, (titre, date, heure_debut, heure_fin, commentaire))
        db.commit()

        ajouter_historique("planning", f"Ajout de l'événement « {titre} »", commentaire)

        flash("Événement ajouté avec succès.", "success")
        return redirect('/agenda/planning')

    return render_template('agenda/formulaire.html')

@app.route('/agenda/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_evenement(id):
    db = get_db()
    evenement = db.execute("SELECT * FROM agenda WHERE id = ?", (id,)).fetchone()

    if not evenement:
        return "Événement introuvable", 404

    if request.method == 'POST':
        titre = request.form['titre']
        date = request.form['date']
        heure_debut = request.form.get('heure_debut') or None
        heure_fin = request.form.get('heure_fin') or None
        annotation = request.form.get('annotation') or None

        db.execute("""
            UPDATE agenda
            SET titre = ?, date = ?, heure_debut = ?, heure_fin = ?, annotation = ?
            WHERE id = ?
        """, (titre, date, heure_debut, heure_fin, annotation, id))
        db.commit()

        ajouter_historique("planning", f"Modification de l'événement « {titre} »", annotation, id)

        flash("Événement mis à jour.", "success")
        return redirect('/agenda/planning')

    return render_template("agenda/formulaire.html", evenement=evenement)

@app.route('/agenda/supprimer/<int:id>', methods=['POST'])
def supprimer_evenement(id):
    db = get_db()
    evenement = db.execute("SELECT * FROM agenda WHERE id = ?", (id,)).fetchone()

    if not evenement:
        return "Événement introuvable", 404

    ajouter_historique("planning", f"Suppression de l'événement « {evenement['titre']} »", evenement['annotation'], id)

    db.execute("DELETE FROM agenda WHERE id = ?", (id,))
    db.commit()

    flash("Événement supprimé.", "warning")
    return redirect('/agenda/planning')

# Documents
@app.route('/documents/liste')
def liste_documents():
    db = get_db()
    recherche = request.args.get('recherche', '').strip()
    type_filtre = request.args.get('type', 'tous')

    where_clauses = []
    params = []

    if recherche:
        where_clauses.append("(titre LIKE ? OR commentaire LIKE ?)")
        params.extend([f"%{recherche}%", f"%{recherche}%"])

    if type_filtre != "tous":
        if type_filtre == "pdf":
            where_clauses.append("type LIKE 'application/pdf'")
        elif type_filtre == "image":
            where_clauses.append("type LIKE 'image/%'")
        elif type_filtre == "word":
            where_clauses.append("type LIKE '%word%'")
        elif type_filtre == "excel":
            where_clauses.append("type LIKE '%excel%'")
        elif type_filtre == "autre":
            where_clauses.append("type NOT LIKE 'application/pdf' AND type NOT LIKE 'image/%' AND type NOT LIKE '%word%' AND type NOT LIKE '%excel%'")

    query = "SELECT * FROM documents_libres"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY date_upload DESC"

    documents = db.execute(query, params).fetchall()

    return render_template("documents/liste.html",
                           documents=documents,
                           recherche=recherche,
                           type=type_filtre)

@app.route('/documents/ajouter', methods=['GET', 'POST'])
def ajouter_document_libre():
    db = get_db()

    if request.method == 'POST':
        titre = request.form['titre']
        commentaire = request.form.get('commentaire') or ''
        fichier = request.files.get('fichier')

        if not fichier or fichier.filename == '':
            flash("Aucun fichier sélectionné.", "warning")
            return redirect('/documents/ajouter')

        base_dir = os.path.dirname(__file__)
        dossier = os.path.join(base_dir, "data", "documents_libres")
        os.makedirs(dossier, exist_ok=True)

        nom_fichier = secure_filename(fichier.filename)
        chemin = os.path.join(dossier, nom_fichier)
        fichier.save(chemin)

        cursor = db.execute("""
            INSERT INTO documents_libres (titre, commentaire, chemin, type)
            VALUES (?, ?, ?, ?)
        """, (titre, commentaire, chemin, fichier.mimetype))

        doc_id = cursor.lastrowid
        db.commit()

        ajouter_historique("document", f"Ajout du document « {titre} »", commentaire, doc_id)

        flash("Document ajouté.", "success")
        return redirect('/documents/liste')

    return render_template('documents/formulaire.html')


@app.route('/documents/voir/<int:id>')
def voir_document_libre(id):
    db = get_db()
    doc = db.execute("SELECT chemin, titre FROM documents_libres WHERE id = ?", (id,)).fetchone()

    if not doc:
        return "Document introuvable", 404

    chemin = doc['chemin']
    if not os.path.isabs(chemin):
        chemin = os.path.join(os.path.dirname(__file__), chemin)

    filename = os.path.basename(chemin)

    return send_file(chemin, as_attachment=False, download_name=filename)


@app.route('/documents/supprimer/<int:id>', methods=['POST'])
def supprimer_document_libre(id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents_libres WHERE id = ?", (id,)).fetchone()

    if not doc:
        return "Document introuvable", 404

    ajouter_historique("document", f"Suppression du document « {doc['titre']} »", doc['commentaire'], id)

    chemin = doc['chemin']
    if not os.path.isabs(chemin):
        chemin = os.path.join(os.path.dirname(__file__), chemin)

    try:
        if os.path.exists(chemin):
            os.remove(chemin)
    except Exception as e:
        print("Erreur suppression fichier :", e)

    db.execute("DELETE FROM documents_libres WHERE id = ?", (id,))
    db.commit()

    flash("Document supprimé.", "warning")
    return redirect('/documents/liste')


# STATISTIQUES
@app.route('/statistiques/tableau_de_bord')
def tableau_de_bord():
    db = get_db()

    # Bateaux
    total_bateaux = db.execute("SELECT COUNT(*) FROM bateaux").fetchone()[0]
    club_bateaux = db.execute("SELECT COUNT(*) FROM bateaux WHERE est_du_club = 1").fetchone()[0]
    hors_club_bateaux = total_bateaux - club_bateaux

    # Emplacements
    total_emplacements = db.execute("SELECT COUNT(*) FROM emplacements").fetchone()[0]
    emplacements_occupees = db.execute("SELECT COUNT(*) FROM emplacements WHERE bateau_id IS NOT NULL").fetchone()[0]
    emplacements_disponibles = total_emplacements - emplacements_occupees
    zones = db.execute("""
        SELECT z.nom AS zone, COUNT(e.id) AS total,
               SUM(CASE WHEN e.bateau_id IS NOT NULL THEN 1 ELSE 0 END) AS occupes
        FROM zones z
        LEFT JOIN emplacements e ON e.zone_id = z.id
        GROUP BY z.id
    """).fetchall()

    # Membres
    total_membres = db.execute("SELECT COUNT(*) FROM membres").fetchone()[0]
    membres_ajour = db.execute("SELECT COUNT(*) FROM membres WHERE cotisation_a_jour = 1").fetchone()[0]
    membres_non_ajour = total_membres - membres_ajour
    pourcentage_membres_ajour = round((membres_ajour / total_membres) * 100) if total_membres else 0

    # Cotisations bateaux (année en cours)
    from datetime import datetime
    annee = datetime.now().year
    total_cotisations = db.execute("SELECT COUNT(*) FROM cotisations WHERE annee = ?", (annee,)).fetchone()[0]
    cotisations_ajour = db.execute("SELECT COUNT(*) FROM cotisations WHERE annee = ? AND est_a_jour = 1", (annee,)).fetchone()[0]
    pourcentage_cotisations_ajour = round((cotisations_ajour / total_cotisations) * 100) if total_cotisations else 0

    # Maintenances
    maintenances_en_cours = db.execute("SELECT COUNT(*) FROM maintenances WHERE statut = 'en cours'").fetchone()[0]
    maintenances_cloturees = db.execute("SELECT COUNT(*) FROM maintenances WHERE statut = 'clôturée'").fetchone()[0]

    return render_template("statistiques/tableau_de_bord.html", 
        total_bateaux=total_bateaux,
        club_bateaux=club_bateaux,
        hors_club_bateaux=hors_club_bateaux,
        total_emplacements=total_emplacements,
        emplacements_occupees=emplacements_occupees,
        emplacements_disponibles=emplacements_disponibles,
        zones=zones,
        total_membres=total_membres,
        membres_ajour=membres_ajour,
        membres_non_ajour=membres_non_ajour,
        pourcentage_membres_ajour=pourcentage_membres_ajour,
        cotisations_ajour=cotisations_ajour,
        total_cotisations=total_cotisations,
        pourcentage_cotisations_ajour=pourcentage_cotisations_ajour,
        maintenances_en_cours=maintenances_en_cours,
        maintenances_cloturees=maintenances_cloturees,
        annee=annee
    )

#HISTORIQUE
@app.route('/historique/interventions')
def historique():
    db = get_db()
    type_filtre = request.args.get('type', 'tous')
    recherche = request.args.get('recherche', '').strip()
    page = int(request.args.get('page', 1))
    par_page = 20
    offset = (page - 1) * par_page

    query = "SELECT * FROM historique WHERE 1=1"
    params = []

    if type_filtre != 'tous':
        query += " AND type = ?"
        params.append(type_filtre)

    if recherche:
        query += " AND (resume LIKE ? OR commentaire LIKE ?)"
        params.extend([f"%{recherche}%", f"%{recherche}%"])

    total_query = f"SELECT COUNT(*) FROM ({query})"
    total = db.execute(total_query, params).fetchone()[0]

    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([par_page, offset])

    resultats = db.execute(query, params).fetchall()

    nb_pages = (total + par_page - 1) // par_page  # arrondi supérieur

    return render_template("historique/liste.html",
                           historiques=resultats,
                           type=type_filtre,
                           recherche=recherche,
                           page=page,
                           nb_pages=nb_pages)

# SAUVEGARDE

# Route pour sauvegarder la base
@app.route('/sauvegarde/export')
def exporter_sauvegarde():
    dossier_data = 'data'
    horodatage = datetime.now().strftime('%Y-%m-%d_%H-%M')
    nom_fichier_zip = f"sauvegarde-{horodatage}.zip"
    chemin_temp = os.path.join("temp", nom_fichier_zip)

    os.makedirs("temp", exist_ok=True)

    with zipfile.ZipFile(chemin_temp, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for dossier_racine, _, fichiers in os.walk(dossier_data):
            for fichier in fichiers:
                chemin_fichier = os.path.join(dossier_racine, fichier)
                chemin_relatif = os.path.relpath(chemin_fichier, dossier_data)
                zipf.write(chemin_fichier, arcname=os.path.join("data", chemin_relatif))

    return send_file(chemin_temp, as_attachment=True)

@app.route('/sauvegarde')
def page_sauvegarde():
    return render_template("sauvegarde/index.html")

@app.route('/sauvegarde/import', methods=['GET', 'POST'])
def importer_sauvegarde():
    from flask import g
    import time
    db_path = os.path.join("data", "app.db")

    if request.method == 'POST':
        if request.form.get("confirmer") != "on":
            flash("Vous devez cocher la case de confirmation.", "warning")
            return redirect('/sauvegarde/import')

        fichier = request.files.get('fichier_zip')
        if not fichier or not fichier.filename.endswith('.zip'):
            flash("Veuillez sélectionner un fichier ZIP valide.", "danger")
            return redirect('/sauvegarde/import')

        nom_fichier = secure_filename(fichier.filename)
        chemin_zip = os.path.join("temp", nom_fichier)
        dossier_temp = os.path.join("temp", "import_temp")
        os.makedirs("temp", exist_ok=True)
        shutil.rmtree(dossier_temp, ignore_errors=True)

        fichier.save(chemin_zip)

        try:
            with zipfile.ZipFile(chemin_zip, 'r') as zip_ref:
                zip_ref.extractall(dossier_temp)

            chemin_data_extrait = os.path.join(dossier_temp, "data")

            # Vérifie qu'on a bien un fichier app.db dans le ZIP
            if not os.path.exists(os.path.join(chemin_data_extrait, "app.db")):
                flash("Le fichier ZIP ne contient pas de base de données valide (app.db).", "danger")
                return redirect('/sauvegarde/import')

            # Ferme proprement la BDD
            if 'db' in g:
                g.db.close()
                g.pop('db', None)

            # Sauvegarde du dossier actuel
            horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
            if os.path.exists("data"):
                shutil.move("data", f"data_backup_{horodatage}")

            # Restauration
            shutil.move(chemin_data_extrait, "data")

            ajouter_historique("système", "Import d'une sauvegarde .zip", nom_fichier)
            flash("Sauvegarde importée avec succès (base app.db restaurée).", "success")

        except Exception as e:
            print("Erreur ZIP :", e)
            flash("Erreur lors de l'import. Vérifiez que le fichier ZIP contient bien un dossier 'data/app.db'.", "danger")

        return redirect('/sauvegarde')

    return render_template("sauvegarde/import.html")




if __name__ == '__main__':
    # Lancement du serveur Flask
    port = 5000
    url = f"http://127.0.0.1:{port}"

    # Lancer le navigateur après une petite pause
    def ouvrir_navigateur():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=ouvrir_navigateur).start()
    app.run(debug=True, port=port)


