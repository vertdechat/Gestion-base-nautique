# Gestion de la base nautique

## Présentation

Cette application web permet de centraliser la gestion quotidienne d'une base nautique. Elle est développée avec [Flask](https://flask.palletsprojects.com/) et stocke ses données dans une base SQLite locale. L'interface propose un tableau de bord unique donnant accès aux différents modules métier : flotte de bateaux, membres, locations, maintenance, fournisseurs, paiements, agenda, documents partagés ou encore statistiques opérationnelles.

## Fonctionnalités principales

- **Gestion des bateaux** : fiche détaillée, filtres, pièces jointes (photos et documents) et suivi de l'appartenance au club.
- **Emplacements et zones** : création d'emplacements, assignation aux bateaux, suivi des disponibilités et historique des affectations.
- **Membres** : annuaire des adhérents, gestion des cotisations, export CSV et suppression en masse.
- **Locations** : planification, disponibilité du matériel, annulations, historique et indicateurs statistiques dédiés.
- **Paiements du port** : suivi des échéances de paiements liés aux bateaux et remise à zéro annuelle.
- **Maintenance** : tickets, tâches, pièces, commentaires, pièces jointes, étiquetage, exports CSV et changement de statut en temps réel.
- **Fournisseurs** : carnet d'adresses, fiches détaillées, export CSV et suivi des contrats.
- **Agenda** : planning des évènements, édition, suppression et visualisation mensuelle.
- **Documents** : dépôt, téléchargement, visualisation et suppression de documents partagés.
- **Statistiques** : tableaux de bord (occupations, locations, finances) pour suivre l'activité de la base.
- **Historique** : journalisation des actions clés (maintenance, sauvegardes, opérations critiques).
- **Sauvegarde & restauration** : export du dossier de données, import d'archives ZIP et restauration automatisée.

## Architecture du projet

- `app.py` contient l'application Flask ainsi que l'ensemble des routes métier.
- `templates/` regroupe les vues HTML (structure basée sur Bootstrap et `layout.html`).
- `static/` contient les ressources statiques (Bootstrap, feuille de style personnalisée, graphique Chart.js, logo).
- `schema.sql` décrit la structure de la base SQLite et `init_db.py` permet de l'initialiser manuellement.
- `data/` accueille la base `app.db` générée au premier lancement (créée automatiquement si absente).
- `lancer.cmd` facilite l'exécution de l'application sous Windows via l'interpréteur embarqué `Python312/`.

## Prérequis

- Python 3.10 ou supérieur.
- `pip` pour installer les dépendances.
- Bibliothèques Python suivantes :
  - `Flask`
  - `Pillow` (gestion des images pour les bateaux et la maintenance)

Sous Windows, un interpréteur Python portable est déjà fourni (`Python312/`) et utilisé par `lancer.cmd`.

## Installation et exécution

1. Cloner le dépôt puis se placer à sa racine.
2. (Recommandé) Créer un environnement virtuel :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Sous Windows : .venv\\Scripts\\activate
   ```
3. Installer les dépendances :
   ```bash
   pip install Flask Pillow
   ```
4. Initialiser la base de données si nécessaire :
   ```bash
   python init_db.py
   ```
   > Au premier lancement, l'application crée également la base automatiquement si `data/app.db` est absent.
5. Démarrer le serveur Flask :
   ```bash
   python app.py
   ```
   L'application est accessible sur `http://127.0.0.1:5000/` et ouvre automatiquement le navigateur par défaut.

## Sauvegarde et restauration

- La page **Sauvegarde** permet d'exporter le dossier `data/` dans une archive ZIP téléchargeable.
- L'import d'une sauvegarde remplace la base actuelle par celle contenue dans l'archive après confirmation et sauvegarde de l'état précédent.

## Ressources supplémentaires

- **Schéma de base** : la structure des tables est définie dans `schema.sql` pour référence.
- **Initialisation** : `init_db.py` est une alternative en ligne de commande à la création automatique.
- **Personnalisation** : les styles peuvent être ajustés dans `static/style.css`, et le logo/branding dans `static/logo.png`.

