import pandas as pd
from io import BytesIO
from database import get_db
from models import Student


def generate_grade_template(course_code):
    """Generate an Excel template pre-filled with student info for grade entry."""
    db = get_db()
    try:
        students = db.query(Student).order_by(Student.nom, Student.prenom).all()
        data = {
            'ID': [s.id for s in students],
            'Nom': [s.nom for s in students],
            'Prenom': [s.prenom for s in students],
            'Note': [''] * len(students),
            'Coefficient': [1.0] * len(students),
        }
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=course_code, index=False)
        output.seek(0)
        return output.getvalue()
    finally:
        db.close()


def parse_grade_excel(contents):
    """Parse an uploaded Excel file containing grades. Returns list of dicts."""
    import base64
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(BytesIO(decoded))

    required_cols = ['ID', 'Note']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Colonne '{col}' manquante dans le fichier.")

    df = df.dropna(subset=['Note'])
    grades = []
    for _, row in df.iterrows():
        grades.append({
            'id_student': int(row['ID']),
            'note': float(row['Note']),
            'coefficient': float(row.get('Coefficient', 1.0)),
        })
    return grades


def parse_import_excel(contents):
    """Parse an uploaded Excel file for full data import (students, courses, grades)."""
    import base64
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    xls = pd.ExcelFile(BytesIO(decoded))

    result = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        result[sheet] = df
    return result
