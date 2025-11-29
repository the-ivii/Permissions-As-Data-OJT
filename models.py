from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base # Imports the Base from file 2

# Association table for Many-to-Many relationship (Role Inheritance)
role_inheritance = Table(
    'role_inheritance',
    Base.metadata,
    Column('parent_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    # Self-referential relationship to find parents
    parents = relationship(
        'Role',
        secondary=role_inheritance,
        primaryjoin=id==role_inheritance.c.child_id,
        secondaryjoin=id==role_inheritance.c.parent_id,
        backref="children"
    )

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    content = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    decision = Column(Boolean, nullable=False)
    explanation = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())