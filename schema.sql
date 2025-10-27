BEGIN TRANSACTION;
DROP TABLE IF EXISTS "cotisations";
CREATE TABLE IF NOT EXISTS "cotisations" (
	"id"	INTEGER,
	"bateau_id"	INTEGER NOT NULL,
	"annee"	INTEGER NOT NULL,
	"est_a_jour"	BOOLEAN DEFAULT 0,
	"mode_paiement"	TEXT CHECK("mode_paiement" IN ('chèque', 'liquide', 'virement', 'carte', 'offert')),
	"date_paiement"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("bateau_id","annee"),
	FOREIGN KEY("bateau_id") REFERENCES "bateaux"("id")
);
DROP TABLE IF EXISTS "zones";
CREATE TABLE IF NOT EXISTS "zones" (
	"id"	INTEGER,
	"nom"	TEXT NOT NULL,
	"type"	TEXT NOT NULL CHECK("type" IN ('port', 'terrain')),
	"couleur"	TEXT,
	"nombre_places"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "emplacements";
CREATE TABLE IF NOT EXISTS "emplacements" (
	"id"	INTEGER,
	"nom"	TEXT NOT NULL,
	"zone_id"	INTEGER NOT NULL,
	"type"	TEXT CHECK("type" IN ('port', 'terrain')),
	"disponible"	BOOLEAN DEFAULT 1,
	"remarque"	TEXT,
	"bateau_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("zone_id") REFERENCES "zones"("id"),
	FOREIGN KEY("bateau_id") REFERENCES "bateaux"("id")
);
DROP TABLE IF EXISTS "bateaux";

CREATE TABLE IF NOT EXISTS "bateaux" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "nom" TEXT NOT NULL,
  "nom_proprietaire" TEXT,
  "photo" TEXT,
  "docx" TEXT,
  "place_port" TEXT,
  "remarques" TEXT,

  "type" TEXT CHECK("type" IN ('voile', 'dériveur', 'moteur', 'catamaran', 'autre')),
  "taille" REAL,
  "couleur_coque" TEXT,
  "couleur_pont" TEXT,
  "annee" INTEGER,
  "categorie" TEXT CHECK("categorie" IN (
    'A-1','A-2','A-6',
    'B-2','B-3','B-4',
    'C-3','C-4','C-5','C-6',
    'D-5','D-6'
  )),
  "est_du_club" BOOLEAN DEFAULT 0,

  "constructeur_modele" TEXT,
  "numero_voile" TEXT,
  "immatriculation" TEXT,
  "date_arrivee" DATE,
  "indisponible" BOOLEAN DEFAULT 0,

  "assurance_nom" TEXT,
  "assurance_numero" TEXT,
  "assurance_coordonnees" TEXT,
  "assurance_tel" TEXT,

  "remorque_au_club" BOOLEAN DEFAULT 0
);

DROP TABLE IF EXISTS "membres";
CREATE TABLE IF NOT EXISTS "membres" (
	"id"	INTEGER,
	"nom"	TEXT NOT NULL,
	"prenom"	TEXT NOT NULL,
	"tel1"	TEXT,
	"tel2"	TEXT,
	"email"	TEXT,
	"date_inscription"	DATE,
	"cotisation_a_jour"	BOOLEAN DEFAULT 0,
	"mode_paiement"	TEXT CHECK("mode_paiement" IN ('chèque', 'liquide', 'virement', 'carte', 'offert')),
	"date_creation"	DATE DEFAULT (date('now')),
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "locations";
CREATE TABLE IF NOT EXISTS "locations" (
	"id"	INTEGER,
	"bateau_id"	INTEGER NOT NULL,
	"membre_id"	INTEGER NOT NULL,
	"debut"	DATETIME NOT NULL,
	"fin"	DATETIME NOT NULL,
	"annule"	BOOLEAN DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("bateau_id") REFERENCES "bateaux"("id"),
	FOREIGN KEY("membre_id") REFERENCES "membres"("id")
);
DROP TABLE IF EXISTS "maintenances";
CREATE TABLE IF NOT EXISTS "maintenances" (
	"id"	INTEGER,
	"titre"	TEXT NOT NULL,
	"description"	TEXT,
	"date_creation"	TEXT DEFAULT (datetime('now')),
	"date_cloture"	TEXT,
	"statut"	TEXT DEFAULT 'planifiée' CHECK("statut" IN ('planifiée', 'en cours', 'clôturée')),
	"priorite"	TEXT DEFAULT 'normale' CHECK("priorite" IN ('haute', 'normale', 'basse')),
	"bateau_id"	INTEGER,
	"categorie"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("bateau_id") REFERENCES "bateaux"("id")
);
DROP TABLE IF EXISTS "taches";
CREATE TABLE IF NOT EXISTS "taches" (
	"id"	INTEGER,
	"maintenance_id"	INTEGER NOT NULL,
	"description"	TEXT NOT NULL,
	"statut"	TEXT DEFAULT 'à faire' CHECK("statut" IN ('à faire', 'en cours', 'terminée')),
	"membre_id"	INTEGER,
	"fournisseur_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id"),
	FOREIGN KEY("membre_id") REFERENCES "membres"("id"),
	FOREIGN KEY("fournisseur_id") REFERENCES "fournisseurs"("id")
);
DROP TABLE IF EXISTS "pieces";
CREATE TABLE IF NOT EXISTS "pieces" (
	"id"	INTEGER,
	"maintenance_id"	INTEGER NOT NULL,
	"nom"	TEXT NOT NULL,
	"quantite"	INTEGER DEFAULT 1,
	"statut_commande"	TEXT DEFAULT 'à commander' CHECK("statut_commande" IN ('à commander', 'commandée', 'reçue', 'installée')),
	"fournisseur_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fournisseur_id") REFERENCES "fournisseurs"("id"),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id")
);
DROP TABLE IF EXISTS "documents";
CREATE TABLE IF NOT EXISTS "documents" (
	"id"	INTEGER,
	"maintenance_id"	INTEGER NOT NULL,
	"nom"	TEXT,
	"type"	TEXT,
	"chemin"	TEXT NOT NULL,
	"date_upload"	TEXT DEFAULT (datetime('now')),
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id")
);
DROP TABLE IF EXISTS "photos";
CREATE TABLE IF NOT EXISTS "photos" (
	"id"	INTEGER,
	"maintenance_id"	INTEGER NOT NULL,
	"chemin"	TEXT NOT NULL,
	"commentaire"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id")
);
DROP TABLE IF EXISTS "commentaires";
CREATE TABLE IF NOT EXISTS "commentaires" (
	"id"	INTEGER,
	"maintenance_id"	INTEGER NOT NULL,
	"texte"	TEXT NOT NULL,
	"auteur"	TEXT,
	"date"	TEXT DEFAULT (datetime('now')),
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id")
);
DROP TABLE IF EXISTS "tags";
CREATE TABLE IF NOT EXISTS "tags" (
	"id"	INTEGER,
	"nom"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "maintenance_tags";
CREATE TABLE IF NOT EXISTS "maintenance_tags" (
	"maintenance_id"	INTEGER NOT NULL,
	"tag_id"	INTEGER NOT NULL,
	PRIMARY KEY("maintenance_id","tag_id"),
	FOREIGN KEY("maintenance_id") REFERENCES "maintenances"("id"),
	FOREIGN KEY("tag_id") REFERENCES "tags"("id")
);
DROP TABLE IF EXISTS "fournisseurs";
CREATE TABLE IF NOT EXISTS "fournisseurs" (
	"id"	INTEGER,
	"nom"	TEXT NOT NULL,
	"siret"	TEXT,
	"site_web"	TEXT,
	"contact"	TEXT,
	"email"	TEXT,
	"telephone"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "agenda";
CREATE TABLE IF NOT EXISTS "agenda" (
	"id"	INTEGER,
	"titre"	TEXT NOT NULL,
	"date"	TEXT NOT NULL,
	"heure_debut"	TEXT,
	"heure_fin"	TEXT,
	"annotation"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "documents_libres";
CREATE TABLE IF NOT EXISTS "documents_libres" (
	"id"	INTEGER,
	"titre"	TEXT NOT NULL,
	"commentaire"	TEXT,
	"chemin"	TEXT NOT NULL,
	"type"	TEXT,
	"date_upload"	TEXT DEFAULT (datetime('now')),
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "historique";
CREATE TABLE IF NOT EXISTS "historique" (
	"id"	INTEGER,
	"date"	TEXT DEFAULT (datetime('now')),
	"type"	TEXT NOT NULL,
	"cible_id"	INTEGER,
	"resume"	TEXT NOT NULL,
	"commentaire"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);


INSERT INTO "tags" ("id","nom") VALUES (1,'gréement');
INSERT INTO "tags" ("id","nom") VALUES (2,'coque');
INSERT INTO "tags" ("id","nom") VALUES (3,'sécurité');
INSERT INTO "tags" ("id","nom") VALUES (4,'quai');
INSERT INTO "tags" ("id","nom") VALUES (5,'électricité');
INSERT INTO "tags" ("id","nom") VALUES (6,'vestiaire');
INSERT INTO "tags" ("id","nom") VALUES (7,'voile');
INSERT INTO "tags" ("id","nom") VALUES (8,'moteur');
INSERT INTO "tags" ("id","nom") VALUES (9,'accastillage');
INSERT INTO "tags" ("id","nom") VALUES (10,'rampe');
INSERT INTO "tags" ("id","nom") VALUES (11,'outillage');
INSERT INTO "tags" ("id","nom") VALUES (12,'ponton');
INSERT INTO "tags" ("id","nom") VALUES (13,'portail');
INSERT INTO "tags" ("id","nom") VALUES (14,'stockage');
INSERT INTO "tags" ("id","nom") VALUES (15,'cordage');
INSERT INTO "tags" ("id","nom") VALUES (16,'dérive');
INSERT INTO "tags" ("id","nom") VALUES (17,'nettoyage');
INSERT INTO "tags" ("id","nom") VALUES (18,'structure');
INSERT INTO "tags" ("id","nom") VALUES (19,'hivernage');
INSERT INTO "tags" ("id","nom") VALUES (20,'signalétique');

COMMIT;
