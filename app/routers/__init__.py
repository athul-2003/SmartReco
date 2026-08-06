"""
Aggregates every router into one, so main.py has a single
`app.include_router(router)` call instead of one per router - each
sub-router already declares its own prefix/tags/dependencies where it
needs them (see e.g. admin.py, catalog.py, recommendations.py), so this
module's only job is assembly.
"""

from fastapi import APIRouter

from app.routers import admin, auth, catalog, events, pages, recommendations

router = APIRouter()
router.include_router(pages.router)
router.include_router(auth.router)
router.include_router(catalog.router)
router.include_router(admin.router)
router.include_router(recommendations.router)
router.include_router(events.router)
