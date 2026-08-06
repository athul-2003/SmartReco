"""
Every SQLModel table needs to be imported somewhere before
`SQLModel.metadata.create_all()` runs (see `app/db.py::init_db`), or its
table never gets registered and never gets created. Importing them all
here - rather than relying on whichever routers/services happen to import
which models - means `import app.models` alone is enough to register the
full schema, decoupled from what else is or isn't wired up elsewhere.
"""

from app.models.event import Event, EventType
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.models.user import Role, User

__all__ = ["Event", "EventType", "Product", "Recommendation", "Role", "User"]
