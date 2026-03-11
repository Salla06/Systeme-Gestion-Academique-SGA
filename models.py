from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(200), unique=True)
    date_naissance = Column(Date)

    grades = relationship('Grade', back_populates='student', cascade='all, delete-orphan')
    absences = relationship('Attendance', back_populates='student', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Student {self.prenom} {self.nom}>"


class Course(Base):
    __tablename__ = 'courses'
    code = Column(String(20), primary_key=True)
    libelle = Column(String(200), nullable=False)
    volume_horaire = Column(Float, nullable=False)
    enseignant = Column(String(200))

    sessions = relationship('Session', back_populates='course', cascade='all, delete-orphan')
    grades = relationship('Grade', back_populates='course', cascade='all, delete-orphan')


class Session(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_course = Column(String(20), ForeignKey('courses.code'), nullable=False)
    date = Column(Date, nullable=False)
    duree = Column(Float, nullable=False)
    theme = Column(String(500))

    course = relationship('Course', back_populates='sessions')
    absences = relationship('Attendance', back_populates='session', cascade='all, delete-orphan')


class Attendance(Base):
    __tablename__ = 'attendance'
    id_session = Column(Integer, ForeignKey('sessions.id'), primary_key=True)
    id_student = Column(Integer, ForeignKey('students.id'), primary_key=True)

    session = relationship('Session', back_populates='absences')
    student = relationship('Student', back_populates='absences')


class Grade(Base):
    __tablename__ = 'grades'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_student = Column(Integer, ForeignKey('students.id'), nullable=False)
    id_course = Column(String(20), ForeignKey('courses.code'), nullable=False)
    note = Column(Float, nullable=False)
    coefficient = Column(Float, default=1.0)

    student = relationship('Student', back_populates='grades')
    course = relationship('Course', back_populates='grades')
