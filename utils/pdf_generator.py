from fpdf import FPDF
from database import get_db
from models import Student, Grade, Course, Session, Attendance
import tempfile
import os


class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Systeme de Gestion Academique', 0, 1, 'C')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, 'Rapport genere automatiquement', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')


def generate_student_bulletin(student_id):
    """Generate a PDF grade bulletin for a student."""
    db = get_db()
    try:
        student = db.query(Student).get(student_id)
        if not student:
            return None

        grades = db.query(Grade).filter(Grade.id_student == student_id).all()

        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_text_color(26, 26, 46)
        pdf.cell(0, 12, 'Bulletin de Notes', 0, 1, 'C')
        pdf.ln(8)

        # Student info box
        pdf.set_fill_color(240, 242, 245)
        pdf.rect(10, pdf.get_y(), 190, 22, 'F')
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(26, 26, 46)
        pdf.cell(95, 10, f'  Etudiant: {student.prenom} {student.nom}', 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(95, 10, f'Email: {student.email or "N/A"}', 0, 1)
        pdf.cell(95, 10, f'  ID: {student.id}', 0, 0)
        dn = student.date_naissance.strftime("%d/%m/%Y") if student.date_naissance else "N/A"
        pdf.cell(95, 10, f'Date de naissance: {dn}', 0, 1)
        pdf.ln(8)

        if not grades:
            pdf.set_font('Helvetica', 'I', 11)
            pdf.cell(0, 10, 'Aucune note enregistree.', 0, 1, 'C')
        else:
            # Table header
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(67, 97, 238)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(30, 9, 'Code', 1, 0, 'C', True)
            pdf.cell(60, 9, 'Matiere', 1, 0, 'C', True)
            pdf.cell(30, 9, 'Note /20', 1, 0, 'C', True)
            pdf.cell(30, 9, 'Coefficient', 1, 0, 'C', True)
            pdf.cell(40, 9, 'Note Ponderee', 1, 1, 'C', True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)

            total_weighted = 0
            total_coeff = 0

            for i, grade in enumerate(grades):
                course = db.query(Course).get(grade.id_course)
                weighted = grade.note * grade.coefficient
                total_weighted += weighted
                total_coeff += grade.coefficient

                bg = (248, 249, 251) if i % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg)
                pdf.cell(30, 8, grade.id_course, 1, 0, 'C', True)
                label = (course.libelle[:28] + '..') if course and len(course.libelle) > 30 else (course.libelle if course else '')
                pdf.cell(60, 8, label, 1, 0, 'L', True)
                pdf.cell(30, 8, f'{grade.note:.2f}', 1, 0, 'C', True)
                pdf.cell(30, 8, f'{grade.coefficient:.1f}', 1, 0, 'C', True)
                pdf.cell(40, 8, f'{weighted:.2f}', 1, 1, 'C', True)

            # Average
            if total_coeff > 0:
                avg = total_weighted / total_coeff
                pdf.ln(3)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_fill_color(26, 26, 46)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(150, 10, '  Moyenne Generale Ponderee:', 0, 0, 'R')
                pdf.cell(40, 10, f' {avg:.2f} / 20', 0, 1, 'C')
                pdf.set_text_color(0, 0, 0)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf.output(tmp.name)
            tmp_path = tmp.name
        
        with open(tmp_path, 'rb') as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
    finally:
        db.close()


def generate_attendance_report(student_id):
    """Generate a PDF attendance report for a student."""
    db = get_db()
    try:
        student = db.query(Student).get(student_id)
        if not student:
            return None

        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_text_color(26, 26, 46)
        pdf.cell(0, 12, 'Rapport de Presence', 0, 1, 'C')
        pdf.ln(8)

        # Student info
        pdf.set_fill_color(240, 242, 245)
        pdf.rect(10, pdf.get_y(), 190, 12, 'F')
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 12, f'  Etudiant: {student.prenom} {student.nom}', 0, 1)
        pdf.ln(6)

        courses = db.query(Course).all()
        total_sessions_all = 0
        total_absences_all = 0

        for course in courses:
            sessions = db.query(Session).filter(Session.id_course == course.code).order_by(Session.date).all()
            if not sessions:
                continue

            absences = db.query(Attendance).join(Session).filter(
                Session.id_course == course.code,
                Attendance.id_student == student_id
            ).count()

            total = len(sessions)
            total_sessions_all += total
            total_absences_all += absences
            rate = ((total - absences) / total) * 100

            # Course header
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(67, 97, 238)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, f'  {course.code} - {course.libelle}', 0, 1, 'L', True)
            pdf.set_text_color(0, 0, 0)

            # Stats
            pdf.set_font('Helvetica', '', 9)
            color = (6, 214, 160) if rate >= 80 else ((253, 126, 20) if rate >= 50 else (239, 71, 111))
            pdf.set_text_color(*color)
            pdf.cell(0, 7, f'    Seances: {total}  |  Absences: {absences}  |  Taux de presence: {rate:.1f}%', 0, 1)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

        # Summary
        if total_sessions_all > 0:
            overall_rate = ((total_sessions_all - total_absences_all) / total_sessions_all) * 100
            pdf.ln(5)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_fill_color(26, 26, 46)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, f'  Taux de presence global: {overall_rate:.1f}%', 0, 1, 'C', True)
            pdf.set_text_color(0, 0, 0)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf.output(tmp.name)
            tmp_path = tmp.name
        
        with open(tmp_path, 'rb') as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
    finally:
        db.close()
