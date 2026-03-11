from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from models import Base, Student, Course, Session, Attendance, Grade

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_db():
    """Get a new database session."""
    return SessionLocal()


def seed_sample_data():
    """Insert sample data if the database is empty."""
    db = get_db()
    try:
        if db.query(Student).count() > 0:
            return

        students = [
            Student(nom="Benali", prenom="Amine", email="amine.benali@univ.dz", date_naissance=date(2002, 3, 15)),
            Student(nom="Hadj", prenom="Sara", email="sara.hadj@univ.dz", date_naissance=date(2001, 7, 22)),
            Student(nom="Mebarki", prenom="Karim", email="karim.mebarki@univ.dz", date_naissance=date(2002, 1, 10)),
            Student(nom="Bouazza", prenom="Lina", email="lina.bouazza@univ.dz", date_naissance=date(2003, 5, 8)),
            Student(nom="Cherif", prenom="Yacine", email="yacine.cherif@univ.dz", date_naissance=date(2002, 11, 30)),
            Student(nom="Taleb", prenom="Nour", email="nour.taleb@univ.dz", date_naissance=date(2001, 9, 14)),
            Student(nom="Kaci", prenom="Mehdi", email="mehdi.kaci@univ.dz", date_naissance=date(2002, 6, 3)),
            Student(nom="Amrani", prenom="Fatima", email="fatima.amrani@univ.dz", date_naissance=date(2003, 2, 19)),
            Student(nom="Djelloul", prenom="Riad", email="riad.djelloul@univ.dz", date_naissance=date(2001, 12, 7)),
            Student(nom="Slimani", prenom="Amira", email="amira.slimani@univ.dz", date_naissance=date(2002, 8, 25)),
            Student(nom="Ferhat", prenom="Sofiane", email="sofiane.ferhat@univ.dz", date_naissance=date(2003, 4, 11)),
            Student(nom="Ziani", prenom="Meriem", email="meriem.ziani@univ.dz", date_naissance=date(2002, 10, 1)),
        ]
        db.add_all(students)
        db.flush()

        courses = [
            Course(code="MATH101", libelle="Mathematiques Fondamentales", volume_horaire=42, enseignant="Dr. Hamidi"),
            Course(code="INFO201", libelle="Programmation Python", volume_horaire=36, enseignant="Prof. Larbi"),
            Course(code="STAT301", libelle="Statistiques Appliquees", volume_horaire=30, enseignant="Dr. Mansouri"),
            Course(code="DATA401", libelle="Data Visualization", volume_horaire=24, enseignant="Prof. Bouzid"),
            Course(code="ALGO102", libelle="Algorithmique Avancee", volume_horaire=36, enseignant="Dr. Khelif"),
        ]
        db.add_all(courses)
        db.flush()

        sessions_data = [
            Session(id_course="MATH101", date=date(2025, 9, 5), duree=3, theme="Introduction aux ensembles"),
            Session(id_course="MATH101", date=date(2025, 9, 12), duree=3, theme="Fonctions et limites"),
            Session(id_course="MATH101", date=date(2025, 9, 19), duree=3, theme="Derivees"),
            Session(id_course="MATH101", date=date(2025, 9, 26), duree=3, theme="Integrales"),
            Session(id_course="INFO201", date=date(2025, 9, 6), duree=3, theme="Variables et types de donnees"),
            Session(id_course="INFO201", date=date(2025, 9, 13), duree=3, theme="Structures de controle"),
            Session(id_course="INFO201", date=date(2025, 9, 20), duree=3, theme="Fonctions et modules"),
            Session(id_course="STAT301", date=date(2025, 9, 7), duree=3, theme="Statistiques descriptives"),
            Session(id_course="STAT301", date=date(2025, 9, 14), duree=3, theme="Probabilites"),
            Session(id_course="DATA401", date=date(2025, 9, 8), duree=3, theme="Introduction a Plotly"),
            Session(id_course="DATA401", date=date(2025, 9, 15), duree=3, theme="Graphiques interactifs"),
        ]
        db.add_all(sessions_data)
        db.flush()

        import random
        random.seed(42)
        for session in sessions_data:
            absent_students = random.sample(students, k=random.randint(0, 3))
            for student in absent_students:
                db.add(Attendance(id_session=session.id, id_student=student.id))

        for student in students:
            for course in courses:
                note = round(random.uniform(6, 19), 2)
                coeff = random.choice([1.0, 1.5, 2.0])
                db.add(Grade(id_student=student.id, id_course=course.code, note=note, coefficient=coeff))

        db.commit()
        print("Sample data inserted successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()
