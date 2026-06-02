"""
repositories router — thin dispatcher.

Endpoints split across four sub-routers:
  router_runs    — analyze, list, get, retry, delete, timeline, by-slug
  router_jit     — issues, prs, diff, similar, file-history, vulnerabilities
  router_meta    — badge, card, featured, trending, spotlight, my-repos, favorites
  router_admin   — stats, rate-limit, pick-spotlight, watched, webhook
"""
from ninja import Router

from .router_runs import router as _runs
from .router_jit import router as _jit
from .router_meta import router as _meta
from .router_admin import router as _admin

router = Router(tags=['repositories'])
router.add_router('', _runs)
router.add_router('', _jit)
router.add_router('', _meta)
router.add_router('', _admin)
