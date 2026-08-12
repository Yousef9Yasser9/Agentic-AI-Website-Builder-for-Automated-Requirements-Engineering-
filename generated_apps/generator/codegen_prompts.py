"""
codegen_prompts.py
==================
System prompts for LLM-based from-scratch code generation (Stage 9).
Every file — including infrastructure — is written by the AI, no Jinja2.
Designed to be concise so llama3.1 8k context fits prompt + context + output.
"""

# ===========================================================================
# INFRASTRUCTURE — db.py
# ===========================================================================
CODEGEN_DB_SYSTEM = """\
Write a complete app/db.py for FastAPI + SQLAlchemy.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

Write EXACTLY this file (copy and paste, filling in the project_slug from context):

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Use SQLite as default (sqlite:///./app.db). Do not import sqlalchemy_utils.
The get_db() function is a FastAPI dependency generator.
"""


# ===========================================================================
# INFRASTRUCTURE — auth.py
# ===========================================================================
CODEGEN_AUTH_SYSTEM = """\
Write a complete app/auth.py for FastAPI with JWT + bcrypt.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

Write EXACTLY this file:

from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt

SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_production_please")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

Output this file as-is. Do not modify the logic.
"""


# ===========================================================================
# INFRASTRUCTURE — deps.py
# ===========================================================================
CODEGEN_DEPS_SYSTEM = """\
Write a complete app/deps.py for FastAPI dependency injection.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

Write EXACTLY this file:

from __future__ import annotations
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import decode_access_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.role or current_user.role.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

def require_role(*roles: str):
    allowed = {r.lower() for r in roles}
    def checker(current_user: models.User = Depends(get_current_user)):
        if not current_user.role or current_user.role.lower() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Required roles: {list(roles)}")
        return current_user
    return checker

Output this file as-is. Do not modify the logic.
"""


# ===========================================================================
# INFRASTRUCTURE — routers/auth.py
# ===========================================================================
CODEGEN_ROUTER_AUTH_SYSTEM = """\
Write a complete app/routers/auth.py FastAPI auth router.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

Write EXACTLY this file:

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uuid

from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token
from app.db import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = models.User(
        id=uuid.uuid4(),
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=getattr(body, "full_name", None),
        role="Customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=schemas.Token)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login/form", response_model=schemas.Token, include_in_schema=False)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user

Output this file as-is. Do not modify the logic.
"""


# ===========================================================================
# BACKEND: models.py
# ===========================================================================
CODEGEN_MODELS_SYSTEM = """\
Write a complete app/models.py for FastAPI + SQLAlchemy.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

REQUIRED IMPORTS (copy exactly):
from __future__ import annotations
import uuid as _uuid
from datetime import datetime, date
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from app.db import Base

REQUIRED GUID CLASS (copy exactly):
class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql": return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(36))
    def process_bind_param(self, value, dialect):
        if value is None: return value
        if dialect.name == "postgresql": return str(value)
        if not isinstance(value, _uuid.UUID): return str(_uuid.UUID(str(value)))
        return str(value)
    def process_result_value(self, value, dialect):
        if value is None: return value
        if not isinstance(value, _uuid.UUID): return _uuid.UUID(str(value))
        return value

TYPE MAPPING:
uuid pk  → Column(GUID, primary_key=True, default=_uuid.uuid4, nullable=False)
uuid fk  → Column(GUID, ForeignKey("tablename.id"), nullable=True)
uuid     → Column(GUID, nullable=True)
string   → Column(String(255), unique=False, nullable=True)
text     → Column(Text, nullable=True)
int      → Column(Integer, nullable=True)
float    → Column(Float, nullable=True)
decimal  → Column(Numeric(12,2), nullable=True)
boolean  → Column(Boolean, default=False, nullable=True)
datetime created_at  → Column(DateTime, default=func.now(), nullable=False)
datetime updated_at  → Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
datetime other       → Column(DateTime, nullable=True)
date     → Column(Date, nullable=True)

RULES:
- Table name = entity name lowercase + 's' (spaces → underscore). User → users, Car → cars
- Use ForeignKey for uuid fields listed in the relationships array
- Set unique=True if field has unique=True
- Add __repr__ returning f"<ClassName id={self.id!r}>" for each class
- Generate ALL entities from the data_model
- The User.role column stores canonical Title Case values such as "Admin" and "Customer".
- Every role comparison must normalize with .lower(); never depend on stored casing.

CRITICAL NULLABLE RULES (prevent seed/constraint errors):
- DEFAULT to nullable=True for ALL non-primary-key fields unless they are explicitly marked required
- Only set nullable=False for: id (pk), email, password_hash, role (on User)
- Date/datetime fields: ALWAYS use nullable=True unless explicitly required
    Examples: return_date, returned_at, completed_at, closed_at, deleted_at, due_date, end_date → nullable=True
- Foreign keys: ALWAYS use nullable=True unless the relationship is mandatory
- String fields: default to nullable=True (use nullable=False only for core identity fields like email)
- NEVER set nullable=False on a field whose value might not exist at creation time
- For User model specifically:
    * id → nullable=False (pk)
    * email → nullable=False (required for login)
    * password_hash → nullable=False (required for auth)
    * role → nullable=False (required for access control)
    * full_name → nullable=True (optional)
    * created_at → nullable=False (auto-set)
    * updated_at → nullable=False (auto-set)
"""


# ===========================================================================
# BACKEND: schemas.py
# ===========================================================================
CODEGEN_SCHEMAS_SYSTEM = """\
Write a complete app/schemas.py for FastAPI + Pydantic v2.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

REQUIRED IMPORTS:
from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

ALWAYS INCLUDE THESE AUTH SCHEMAS:
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)  # IMPORTANT: "password" not "password_hash" - server hashes it!
    full_name: Optional[str] = None
    role: str = "Customer"

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None  # Plain password for updates, server hashes it
    full_name: Optional[str] = None
    role: Optional[str] = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    role: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None

FOR EACH NON-USER ENTITY generate exactly three Pydantic classes:
1. {Name}Create(BaseModel)   — all fields except id, created_at, updated_at
2. {Name}Update(BaseModel)   — all fields Optional
3. {Name}Read(BaseModel)     — all fields, model_config=ConfigDict(from_attributes=True)

TYPE MAPPING for schemas:
uuid    → UUID (Optional[UUID]=None if nullable)
string/text → str (Optional[str]=None if nullable, else str)
int     → int (Optional[int]=None)
float/decimal → float (Optional[float]=None)
boolean → bool = False
datetime → Optional[datetime] = None
date    → Optional[date] = None
"""


# ===========================================================================
# BACKEND: main.py   (FIXED — instructions only, no confusing code skeleton)
# ===========================================================================
CODEGEN_MAIN_SYSTEM = """\
Write a complete app/main.py for FastAPI. Use the JSON context to fill in project details.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

STEP 1 — Copy these imports and helpers verbatim at the top of the file:

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os as _os

from app.db import engine, Base
from app.routers.auth import router as auth_router
from app.routers.generic_crud import router as crud_router

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend_templates"

def _html(filename: str, entity: str = None) -> Response:
    path = _FRONTEND_DIR / filename
    if not path.exists():
        return JSONResponse({"error": f"{filename} not found"}, status_code=404)
    content = path.read_text(encoding="utf-8")
    if entity:
        js = f'<script>window.ENTITY_OVERRIDE="{entity.lower()}s";window.ENTITY_SINGULAR_OVERRIDE="{entity.lower()}";</script>'
        content = content.replace("</head>", js + "\\n</head>") if "</head>" in content else js + content
    return Response(content=content, media_type="text/html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

STEP 2 — Create the FastAPI app using the project_title from context:

app = FastAPI(title="<project_title>", description="Auto-generated by AI Website Builder", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(crud_router)

STEP 3 — Add these fixed auth/health routes:

@app.get("/ui/login", response_class=Response, include_in_schema=False)
def ui_login(): return _html("login.html")

@app.get("/ui/register", response_class=Response, include_in_schema=False)
def ui_register(): return _html("register.html")

@app.get("/", response_class=Response, include_in_schema=False)
def ui_root(): return _html("app.html")

@app.get("/admin/dashboard", response_class=Response, include_in_schema=False)
def ui_admin(): return _html("app.html")

@app.get("/health", tags=["health"])
def health(): return {"status": "ok", "project": "<project_title>"}

STEP 4 — For each entity in data_model.entities where name is NOT "User":
  Let R = entity name lowercased with spaces replaced by underscore (e.g. "Book Loan" -> "book_loan")
  Add three routes:
    @app.get("/ui/{R}s", response_class=Response, include_in_schema=False)
    def ui_list_{R}(): return _html("entity_list.html", entity="<EntityName>")

    @app.get("/ui/{R}s/new", response_class=Response, include_in_schema=False)
    def ui_new_{R}(): return _html("entity_form.html", entity="<EntityName>")

    @app.get("/ui/{R}s/{item_id}/edit", response_class=Response, include_in_schema=False)
    def ui_edit_{R}(item_id: str): return _html("entity_form.html", entity="<EntityName>")

STEP 5 — For each page in architecture.pages:
  If page.path does NOT start with /ui/ and is NOT "/" and is NOT "/admin/dashboard":
    Add: @app.get("<page.path>", response_class=Response, include_in_schema=False)
    def ui_page_<index>(request: Request): return _html("app.html")

STEP 6 — Add the guaranteed dashboard statistics endpoint:

@app.get("/api/dashboard/stats", tags=["dashboard"])
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stats = {}
    # Generate one count per non-User entity:
    # stats["books"] = db.query(models.Book).count()
    return stats

Import Depends, Session, models, get_db, and get_current_user for this route.

IMPORTANT RULES:
- Every function name must be unique. Use entity name + action (ui_list_book, ui_new_book, etc.)
- Replace <project_title> with the actual title from context
- Replace <EntityName> with the actual entity name (e.g. "Book")
- Replace <R> with the resource slug (e.g. "book")
- The edit route MUST have item_id: str as a parameter
- Do NOT add duplicate routes
"""


# ===========================================================================
# BACKEND: generic_crud.py
# ===========================================================================
CODEGEN_CRUD_SYSTEM = """\
Write a complete app/routers/generic_crud.py for FastAPI.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

REQUIRED IMPORTS:
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.deps import get_db, get_current_user, require_admin
from app import models, schemas

router = APIRouter(prefix="/api", tags=["crud"])

FOR EACH NON-USER ENTITY in data_model generate 5 endpoints:

GET    /api/{resources}         List all records. Auth required.
POST   /api/{resources}         Create. Auth required.
GET    /api/{resources}/{id}    Get one. Auth required.
PUT    /api/{resources}/{id}    Update. Auth required.
DELETE /api/{resources}/{id}    Delete. Admin required.

Where {resources} = entity.name.lower().replace(' ','_').replace('-','_') + 's'

CRITICAL RULES:
1. ALL endpoints take: db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
2. Enforce role_access from architecture. Admin can access every record; a Customer
   may mutate only an owned record when that operation is allowed by architecture.
3. Return 404 HTTPException if item not found (not 500!)
4. On create: ALWAYS generate UUID: data = body.model_dump(exclude_unset=True); if 'id' not in data: data['id'] = str(uuid.uuid4())
5. On update: MUST use model_dump(exclude_unset=True) NOT dict()
6. Each entity uses correct Schema classes: {Entity}Create, {Entity}Update, {Entity}Read
7. Function names MUST be unique: list_{resource}, create_{resource}, get_{resource}, update_{resource}, delete_{resource}
8. DELETE endpoint returns status 204 No Content, NO response_model
9. Wrap all DB operations in try-except to catch IntegrityError and return 400 Bad Request
10. NEVER use .dict() - ALWAYS use .model_dump() (Pydantic v2)

OWNERSHIP FILTERING RULES:
- If an entity has user_id, owner_id, created_by, customer_id, or uploader_id, non-admin users only see their own records.
- Admin users see all records.
- Apply ownership filtering in list, get, update, and delete operations.
- When creating an owned record as a non-admin, force its ownership field to current_user.id.
- Never trust a customer-supplied ownership field.
- For get/update/delete, build the ownership-scoped query before calling .first().
  Never fetch an arbitrary row and check ownership afterward.

Canonical list/get pattern:
    query = db.query(models.Entity)
    owner_field = next((name for name in ("user_id", "owner_id", "created_by", "customer_id", "uploader_id") if hasattr(models.Entity, name)), None)
    if current_user.role.lower() != "admin" and owner_field:
        query = query.filter(getattr(models.Entity, owner_field) == current_user.id)

EXAMPLE TEMPLATE FOR EACH ENTITY:

# ---- {EntityName} ----
@router.get("/{resources}", response_model=List[schemas.{Entity}Read])
def list_{resources}(
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.{Entity}).offset(skip).limit(limit).all()

@router.get("/{resources}/{{item_id}}", response_model=schemas.{Entity}Read)
def get_{resource}(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    obj = db.query(models.{Entity}).filter(models.{Entity}.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="{Entity} not found")
    return obj

@router.post("/{resources}", response_model=schemas.{Entity}Read, status_code=201)
def create_{resource}(
    body: schemas.{Entity}Create,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        data = body.model_dump(exclude_unset=True)
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())
        obj = models.{Entity}(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create {Entity}: {{str(e)}}")

@router.put("/{resources}/{{item_id}}", response_model=schemas.{Entity}Read)
def update_{resource}(
    item_id: str,
    body: schemas.{Entity}Update,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    obj = db.query(models.{Entity}).filter(models.{Entity}.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="{Entity} not found")
    try:
        update_data = body.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
        return obj
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update {Entity}: {{str(e)}}")

@router.delete("/{resources}/{{item_id}}", status_code=204)
def delete_{resource}(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    obj = db.query(models.{Entity}).filter(models.{Entity}.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="{Entity} not found")
    try:
        db.delete(obj)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete {Entity}: {{str(e)}}")

GENERATE ALL 5 ENDPOINTS FOR EACH NON-USER ENTITY. Use proper error handling with try-except.
"""


# ===========================================================================
# BACKEND: seed.py
# ===========================================================================
CODEGEN_SEED_SYSTEM = """\
Write a complete seed.py database seeder script.

OUTPUT: Raw Python ONLY. No markdown. No backticks. No explanations.

REQUIRED STRUCTURE — copy this skeleton and fill in the entity data:

import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DATABASE_URL", "sqlite:///./app.db")

from app.db import engine, Base, SessionLocal
from app import models
import uuid
from datetime import datetime, date, timezone, timedelta

def now():
    return datetime.now(timezone.utc)

def today():
    return date.today()

def days_ago(n):
    return today() - timedelta(days=n)

def days_from_now(n):
    return today() + timedelta(days=n)

def main():
    # Idempotent: preserve existing data and create only missing tables/rows.
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        from app.auth import hash_password

        # Create admin user
        admin = db.query(models.User).filter_by(email="admin@example.com").first()
        if not admin:
            admin = models.User(
                id=uuid.uuid4(),
                email="admin@example.com",
                password_hash=hash_password("Admin1234!"),
                role="Admin",
                full_name="System Administrator",
                created_at=now(),
                updated_at=now()
            )
            db.add(admin)
        admin_id = admin.id

        # Create regular user
        user = db.query(models.User).filter_by(email="user@example.com").first()
        if not user:
            user = models.User(
                id=uuid.uuid4(),
                email="user@example.com",
                password_hash=hash_password("User1234!"),
                role="Customer",
                full_name="Sample User",
                created_at=now(),
                updated_at=now()
            )
            db.add(user)
        db.flush()
        user_id = user.id

        # --- ADD 5-8 REALISTIC RECORDS FOR EACH NON-USER ENTITY HERE ---
        # CRITICAL RULES:
        # 1. ALWAYS set created_at=now() and updated_at=now() for EVERY entity
        # 2. ALWAYS use uuid.uuid4() for id fields
        # 3. For foreign keys, use admin_id or user_id (already created above)
        # 4. For date fields, use today(), days_ago(n), or days_from_now(n)
        # 5. For datetime fields, use now()
        # 6. NEVER pass None for any field - always provide a value
        # 7. For optional fields, provide sensible defaults (empty string, 0, False, today(), etc.)
        # 8. Use domain-appropriate realistic data based on project_title

        db.commit()
        print("Database seeded successfully!")
        print("Admin: admin@example.com / Admin1234!")
        print("User: user@example.com / User1234!")
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

EXAMPLE FOR A LIBRARY SYSTEM:
# Book entity
book1_id = uuid.uuid4()
book1 = models.Book(
    id=book1_id,
    title="The Great Gatsby",
    author="F. Scott Fitzgerald",
    isbn="978-0-7432-7356-5",
    quantity=5,
    available=5,
    created_at=now(),
    updated_at=now()
)
db.add(book1)

# Loan entity (with foreign keys)
loan1_id = uuid.uuid4()
loan1 = models.Loan(
    id=loan1_id,
    book_id=book1_id,
    member_id=user_id,
    borrowed_date=days_ago(7),
    due_date=days_from_now(7),
    returned_date=None,  # Optional field - can be None for active loans
    status="active",
    created_at=now(),
    updated_at=now()
)
db.add(loan1)

INSTRUCTIONS:
1. Generate 5-8 realistic records for EACH entity in data_model.entities that is NOT User
2. Use DOMAIN-APPROPRIATE realistic data (not lorem ipsum) based on project_title
3. Set ALL foreign key fields using admin_id or user_id (already created above)
4. Use uuid.uuid4() for each record's id field
5. ALWAYS set created_at=now() and updated_at=now() for EVERY entity
6. For date fields use today(), days_ago(n), or days_from_now(n)
7. For datetime fields use now()
8. For optional/nullable fields that should be empty, you CAN use None (like returned_date for active loans)
9. For required fields, ALWAYS provide a value - never None
10. Use ASCII-only strings in print() calls
11. User roles MUST use canonical Title Case: "Admin" and "Customer".
12. Do NOT invent fields that don't exist in the models - only use fields defined in data_model
13. NEVER call Base.metadata.drop_all(). Every seed operation must use get-or-create checks.
14. Domain sample rows must also be idempotent: check a stable natural key, or skip
    seeding an entity when it already has rows. Running seed.py twice must not duplicate data.
"""


# ===========================================================================
# FRONTEND: standalone landing HTML
# ===========================================================================
CODEGEN_BASE_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, STUNNING Landing Page for the web application.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: The name of the application.
- theme: The theme color variables (primary, accent, bg, surface, text, text_muted, font_heading, font_body).
- architecture: The routing and user roles configuration.

DESIGN & STYLE REQUIREMENTS:
1. Brand Aesthetic: Use Montserrat for headings and Playfair Display (or fonts defined in the theme context) for primary visual text. Deliver a highly premium, custom design.
2. Premium Theme: Set theme colors in a CSS variable block in <style> using the provided theme variables. Create a beautiful glassmorphism effect (blur, semi-transparent panels) and sleek ambient animated backgrounds (using CSS keyframes for floating glowing gradient nodes).
3. Visual Showcase:
   - Modern hero section with bold typography, a dynamic gradient title, and call-to-action buttons leading to "/ui/login" and "/ui/register".
   - Feature grid showcasing the application's main modules based on the roles and pages in the context.
   - Elegant dark theme with custom glowing hover animations, border glow transitions, and responsive layout.
4. Navigation: Top navbar with a brand logo and buttons to "/ui/login" and "/ui/register".

Output ONLY the complete, raw standalone HTML code.
"""


# ===========================================================================
# FRONTEND: standalone login HTML
# ===========================================================================
CODEGEN_LOGIN_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, STUNNING Login Page.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: Name of the application.
- theme: Theme color variables.

DESIGN & FUNCTIONAL REQUIREMENTS:
1. Premium Glassmorphic Card: Place the login form inside a card with extreme blur backdrop filter (`backdrop-filter: blur(20px)`), glowing borders on focus, and smooth entry animation (fade-in / slide-up).
2. Background: Dynamic CSS moving gradients or particle-like animated glowing radial circles in the background to feel alive.
3. Form Fields:
   - Form ID: "login-form"
   - Email Input ID: "login-email"
   - Password Input ID: "login-password"
   - Link: To "/ui/register" for registration.
4. Typography & Color: Use primary, bg, surface, and text colors directly in a custom <style> block matching the provided theme context. Include Google Fonts imports.
5. Interactive Logic:
   - Self-contained `<script>` including standard auth helpers (`getToken`, `getUser`, `isLoggedIn`, `logout`, `flash`, `authHeaders`, `apiFetch`).
   - Form submit listener that captures email and password, executes a POST request to `/api/auth/login` with JSON payload `{email, password}`.
   - On success: Store the token under `access_token`, call `/api/auth/me` with that
     token, store the returned profile under `current_user`, then redirect to `/`.
   - On error: Calls the custom `flash(errorMessage)` to show a clean floating banner notification.

Output ONLY the complete, raw standalone HTML code.
"""


# ===========================================================================
# FRONTEND: standalone register HTML
# ===========================================================================
CODEGEN_REGISTER_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, STUNNING Registration Page.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: Name of the application.
- theme: Theme color variables.

DESIGN & FUNCTIONAL REQUIREMENTS:
1. Matching Visual Style: Seamless integration with the Login page's premium dark glassmorphism, animated backgrounds, and custom fonts.
2. Form Fields:
   - Form ID: "register-form"
   - Full Name Input ID: "reg-name"
   - Email Input ID: "reg-email"
   - Password Input ID: "reg-password"
   - Confirm Password Input ID: "reg-confirm"
   - Password Toggle: Include a beautiful eye icon to show/hide the password.
   - Link: Back to "/ui/login".
3. Interactive Logic:
   - Self-contained script with standard auth helpers.
   - Submit listener that checks if password matches confirm, then sends a POST request to `/api/auth/register` with JSON payload `{email, password, full_name, role: 'Customer'}`.
   - On success: Triggers `flash("Account created! Redirecting to login...", "success")` and redirects to `/ui/login` after 1.5 seconds.
   - On error: Triggers `flash(errorMessage)` with the error details.

Output ONLY the complete, raw standalone HTML code.
"""


# ===========================================================================
# FRONTEND: standalone application dashboard HTML
# ===========================================================================
CODEGEN_DASHBOARD_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, PREMIUM Application Dashboard.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: Name of the application.
- theme: Theme variables (primary, accent, bg, surface, text, text_muted, font_heading, font_body).
- architecture: Complete page routes and user roles.
- data_model: Database entities.

DESIGN & FEATURE REQUIREMENTS:
1. Standalone Architecture: Define a cohesive dark UI layout with a premium responsive Sidebar Navigation containing all pages and list views from the architecture context. Add custom scrollbars, glowing active states, user profile badges, and a glassmorphism theme layout.
2. Bespoke Brand Elements: Make the dashboard styling tailored specifically to the application's domain (e.g. customized gradients, relevant emojis/icons, premium typography like Montserrat & Playfair Display).
3. Stat Cards & Echarts/SVGs:
   - Dynamic cards representing each database entity (e.g. Books, Members, Loans).
   - Each card must display the entity name and have a dynamic counter element with a unique ID: `count-{entity_name_plural}` (e.g. `count-books`, `count-members`).
   - Incorporate clean, pure CSS/SVG visual graphs (e.g. progress bars, glowing grid lines) to feel highly analytical.
4. Interactive Logic:
   - Script starts with a security guard checking `isLoggedIn()`. If false, redirect to `/ui/login?next=/`. If true, verify role-access.
   - Greets user dynamically based on the stored `current_user` email (extracted username prefix) in the dashboard header banner.
   - Load `/api/dashboard/stats` first and map its numeric values to the counter cards.
     If one stat is absent, gracefully fall back to that entity's list endpoint.
   - Quick Actions: Includes shortcuts to create new entity items (`/ui/{entity}s/new`) and view lists (`/ui/{entity}s`).

Output ONLY the complete, raw standalone HTML code.
"""


# ===========================================================================
# FRONTEND: standalone reusable entity list HTML
# ===========================================================================
CODEGEN_LIST_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, PREMIUM Entity List page that acts as a generic, reusable data grid.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: Name of the application.
- theme: Theme variables.
- architecture: Sidebar navigation context.
- data_model: Database entities.

DESIGN & REUSABLE ENGINE REQUIREMENTS:
1. Cohesive Visual Frame: Shared layout with the sidebar navigation, premium headers, custom action buttons, search fields, and glassmorphic tables.
2. Dynamic Reusable Javascript Engine:
   - Script extracts entity information:
     `const entity = window.ENTITY_OVERRIDE || 'records';`
     `const entitySingular = window.ENTITY_SINGULAR_OVERRIDE || entity.replace(/s$/, '');`
   - Dynamically updates the page title, section headers, and "Create New" buttons to match the active entity name (e.g. "Manage Books", "New Book" linking to `/ui/{entity}/new`).
   - AJAX Records Loader: Fetches JSON data from `/api/` + entity via `apiFetch`.
   - Dynamic Header Generator: If data exists, inspect the keys of the first record `Object.keys(rows[0])` (filtering out security columns like `password_hash`). Render these keys as `<th>` columns dynamically with interactive hover sorting states.
   - Dynamic Row Populator: Maps the columns to table row `<td>` elements. Beautify values (e.g. format dates nicely, render booleans as colorful green/red badges).
   - Table Actions: Add custom edit links (`/ui/${entity}/${row.id}/edit`) and a delete button.
   - Interactivity:
     - Header Sort: Clicking on any table header sorts the table rows alphabetically/numerically (ascending/descending arrow indicator toggles).
     - Search Box (ID: "search-input"): Keypress filtering that hides table rows not containing the searched term.
     - Delete Hook: Calls `DELETE /api/{entity}/{id}` after confirmation, showing success flash and refreshing list.
3. Security Guard: Redirects unauthorized users to `/ui/login` and handles role-based panel visibility.

Output ONLY the complete, raw standalone HTML code.
"""


# ===========================================================================
# FRONTEND: standalone reusable entity form HTML
# ===========================================================================
CODEGEN_FORM_HTML_SYSTEM = """\
Write a COMPLETE, STANDALONE, PREMIUM Entity Form page that acts as a reusable schema-based editor.

OUTPUT: Raw HTML ONLY. No markdown. No backticks. No explanations. No Jinja2 template tags like {% extends %}, {% block %}, or block syntax. It must be a 100% complete and self-contained HTML document.

CONTEXT JSON contains:
- project_title: Name of the application.
- theme: Theme variables.
- architecture: Sidebar navigation.
- data_model: Complete database entities with fields, types, and constraints.

DESIGN & SCHEMA-BASED ENGINE REQUIREMENTS:
1. Glassmorphic Form Container: Centered elegant form card with input focus glows, smooth focus border transitions, back buttons, and beautiful visual structure.
2. Intelligent Client-Side Schema Mapper:
   - Inside the `<script>`, the LLM must generate a javascript dictionary `const SCHEMA_MAP = { ... }` derived from the provided `data_model` context!
   - Each dictionary entry maps the entity singular name (e.g. `book`, `member`, `borrowed_book`) to an array of its database columns (including: name, label, type [text, number, date, select, checkbox], placeholders, required booleans, and any relational foreign key selectors).
   - Dynamic Input Renderer: On page load, reads `window.ENTITY_SINGULAR_OVERRIDE` and dynamically renders the exact input fields, labels, and validation attributes in the form container!
   - Select field choices: If a field is a foreign key relation (e.g., `book_id`), the script runs an AJAX fetch to `/api/books` to populate the dropdown options with realistic records!
3. Edit/Prepopulation Logic:
   - Detects if editing by parsing the URL path for an ID (e.g., `/ui/{entity}/{id}/edit`).
   - If ID is present, changes form headers to "Edit {Entity}" and submit buttons to "Update".
   - Executes an AJAX fetch to `/api/{entity}/{id}` and automatically prepopulates all dynamic input fields.
4. Save & Submit Hook:
   - Intercepts form submit, gathers all form values into a JSON object (excluding empty values), and executes a PUT (if editing) or POST (if new) request to `/api/{entity}`.
   - Shows a success flash and redirects the user back to the list view `/ui/{entity}` on successful save.

Output ONLY the complete, raw standalone HTML code.
"""


CANONICAL_AUTH_HELPERS = r"""
MANDATORY JAVASCRIPT — copy this block exactly into the page:

// === CANONICAL AUTH HELPERS ===
function getToken() { return localStorage.getItem('access_token'); }
function getUser() { try { return JSON.parse(localStorage.getItem('current_user') || 'null'); } catch { return null; } }
function isLoggedIn() { return !!getToken(); }
function logout() { localStorage.removeItem('access_token'); localStorage.removeItem('current_user'); window.location.href = '/ui/login'; }
function authHeaders() { return { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' }; }
async function apiFetch(path, options = {}) {
    options.headers = { ...authHeaders(), ...(options.headers || {}) };
    const response = await fetch(path, options);
    if (response.status === 401) { logout(); return null; }
    if (!response.ok) {
        let message = `Request failed (${response.status})`;
        try {
            const payload = await response.clone().json();
            message = payload.detail || payload.error || message;
        } catch {}
        flash(message);
        throw new Error(message);
    }
    return response;
}
function flash(message, type = 'error') {
    const element = document.getElementById('flash-msg') || document.createElement('div');
    element.id = 'flash-msg';
    element.textContent = message;
    element.style.cssText = `position:fixed;top:20px;right:20px;padding:12px 24px;border-radius:8px;z-index:9999;font-weight:600;background:${type === 'success' ? '#22c55e' : '#ef4444'};color:#fff;`;
    document.body.appendChild(element);
    setTimeout(() => element.remove(), 3500);
}
// === END CANONICAL AUTH HELPERS ===

Use only the localStorage keys access_token and current_user. Do not introduce a token key.
"""

CODEGEN_LOGIN_HTML_SYSTEM += CANONICAL_AUTH_HELPERS
CODEGEN_REGISTER_HTML_SYSTEM += CANONICAL_AUTH_HELPERS
CODEGEN_DASHBOARD_HTML_SYSTEM += CANONICAL_AUTH_HELPERS
CODEGEN_LIST_HTML_SYSTEM += CANONICAL_AUTH_HELPERS
CODEGEN_FORM_HTML_SYSTEM += CANONICAL_AUTH_HELPERS
