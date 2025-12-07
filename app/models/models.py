"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Association table for Many-to-Many relationship (Role Inheritance)
# parent_id: References the parent role.
# child_id: References the child role
# Both are primary keys forming a composite key
role_inheritance = Table(
    'role_inheritance',
    Base.metadata,
    Column('parent_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

# Represents user role with inheritance.
# Fields:
# 1. id: primary key
# 2. name: unique role name, indexed
# 3. description: optional role description
#
# Relationships:
# 1. parents: Many-to-Many relationship to itself (through role_inheritance table)
# 2. children: Self-referential relationship to find children roles via backref "children"
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    # Self-referential relationship to find parents
    parents = relationship(
        'Role',
        secondary=role_inheritance,
        primaryjoin=id==role_inheritance.c.child_id,  # primaryjoin: join condition for the primary side
        secondaryjoin=id==role_inheritance.c.parent_id,  # secondaryjoin: join condition for the secondary side
        backref="children"  # backref: allows easy access to the children roles from the parent role
    )


# Store authorisation policy with versioning
class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    content = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Logs all authorisation decisions for auditing and debugging.
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)  # the user/role making the request
    action = Column(String, nullable=False)  # action attempted
    resource = Column(String, nullable=False)  # resource tried to access
    decision = Column(Boolean, nullable=False)  # allow or deny (true or false)
    explanation = Column(String, nullable=True)  # reason for the decision
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

