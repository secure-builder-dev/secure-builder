id: TQ-1a
unit: TQ-1
state: in review
depends_on: -
done_when: backend/app/db.py reads the database URL from the environment variable TICKETER_DATABASE_URL when it is imported and raises RuntimeError when the variable is unset or empty (there is no built-in default URL); db.py defines engine (the SQLAlchemy engine for that URL), Base (a subclass of sqlalchemy.orm.DeclarativeBase), SessionLocal (a sessionmaker bound to engine) and init_db(), which imports app.models and creates every table; backend/app/models.py defines the model Ticket on Base with the table name tickets and exactly the columns id (Integer primary key), title (String(120)), details (String(1000), default ''), priority (String), due (Date, nullable), status (String), filed_by (String), assigned_to (String), created_at and updated_at (DateTime(timezone=True))

# TQ-1a
