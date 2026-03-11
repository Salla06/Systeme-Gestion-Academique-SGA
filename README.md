# SGA - Systeme de Gestion Academique

Application web de gestion academique developpee avec Python Dash, SQLAlchemy et SQLite.

## Fonctionnalites

### Module 0 : Persistance et Migration
- Creation automatique des tables SQL au lancement
- Import de donnees depuis fichiers Excel (.xlsx, .xls)
- Gestion des doublons avec messages informatifs

### Module 1 : Gestion des Cours (Curriculum)
- Interface CRUD complete (ajout, modification, suppression)
- Suivi de progression en temps reel (heures effectuees / volume total)
- Affichage du nombre de seances par cours

### Module 2 : Cahier de Texte et Presences
- Enregistrement des seances avec theme aborde
- Appel numerique avec liste de cases a cocher
- Historique triable par date ou par cours

### Module 3 : Gestion des Etudiants et Evaluations
- Fiche individuelle avec moyenne et taux de presence
- Workflow Excel : telechargement de template et import de notes
- Validation des notes (plage 0-20)
- Validation du format email
- Generation de bulletins PDF et rapports de presence

### Tableau de Bord
- Statistiques globales (etudiants, cours, seances, moyenne)
- Filtrage par cours
- Graphiques interactifs (distribution des notes, presence, moyennes)
- Rafraichissement automatique toutes les 30 secondes

## Structure du Projet

```
sga/
├── app.py                 # Point d'entree de l'application
├── config.py              # Configuration (database, uploads)
├── database.py            # Initialisation et seeding de la base
├── models.py              # Modeles SQLAlchemy
├── pages/
│   ├── home.py            # Tableau de bord
│   ├── courses.py         # Gestion des cours
│   ├── sessions.py        # Seances et presences
│   ├── students.py        # Gestion des etudiants
│   ├── grades.py          # Notes et evaluations
│   └── import_data.py     # Import Excel
├── utils/
│   ├── excel_utils.py     # Fonctions Excel
│   └── pdf_generator.py   # Generation PDF
└── assets/
    └── custom.css         # Styles personnalises
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python app.py
```

L'application sera accessible sur http://localhost:8050

## Dependances

- dash >= 2.14.0
- dash-bootstrap-components >= 1.5.0
- sqlalchemy >= 2.0.0
- pandas >= 2.0.0
- openpyxl >= 3.1.0
- fpdf2 >= 2.7.0
- plotly >= 5.18.0

## Format des Fichiers Excel pour Import

### Feuille Etudiants
Colonnes : ID, Nom, Prenom, Email, Date_Naissance

### Feuille Cours
Colonnes : Code, Libelle, Volume_Horaire, Enseignant

### Feuille Notes
Colonnes : ID_Student, Code_Cours, Note, Coefficient

Les noms de colonnes sont flexibles et acceptent plusieurs variations.

## Auteur

Projet de Data Visualization avec Dash
