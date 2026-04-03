import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mes.config import settings
from mes.framework.api.exceptions import register_exception_handlers
from mes.framework.auth.routes import router as auth_router
from mes.framework.events import event_bus
from mes.framework.events.decorators import get_registered_handlers
from mes.framework.events.gateway import router as events_router
from mes.framework.plugin import PluginManager

# Core module routers (Layer 1+)
from mes.core.physical_model.routes import router as physical_model_router
from mes.core.product_def.routes import router as product_def_router
from mes.core.uom.routes import router as uom_router

# Layer 2 routers
from mes.core.production.routes import router as production_router
from mes.core.wip.routes import router as wip_router

# Layer 3 routers
from mes.core.material.routes import router as material_router
from mes.core.data_collection.routes import router as data_collection_router

# Layer 4 routers
from mes.core.quality.routes import router as quality_router
from mes.core.performance.routes import router as performance_router
from mes.core.genealogy.routes import router as genealogy_router
from mes.core.dispatch.routes import router as dispatch_router
import mes.core.dispatch.handlers  # registers @event_handler decorators  # noqa: F401

# Integration adapter routers (P4)
from mes.adapters.erp.routes import router as erp_queue_router
import mes.adapters.erp.handlers  # registers ERP outbound @event_handler decorators  # noqa: F401

# Dashboard aggregation routes
from mes.core.dashboard.routes import router as dashboard_router

# Plugin management routes
from mes.framework.plugin.routes import router as plugin_router

logger = logging.getLogger("mes")

# Module-level singletons
plugin_manager = PluginManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Startup: register event handlers, discover plugins, load installed+enabled, seed default roles.
    Shutdown: stop plugins, clean up.
    """
    logger.info("MES AI server starting (v%s)", settings.VERSION)

    # Register decorated event handlers with the global event bus
    for topic, handler in get_registered_handlers():
        event_bus.subscribe(topic, handler)

    # Discover all plugins from system + user directories
    await plugin_manager.discover_all()

    # Determine which plugins are installed + enabled from DB
    installed_ids = await _get_installed_enabled_plugin_ids()

    # Load and start installed + enabled plugins
    await plugin_manager.load_and_start(installed_ids)

    # Register plugin routes
    for router in await plugin_manager.get_plugin_routes():
        app.include_router(router)

    logger.info("MES AI server ready")
    yield

    # Shutdown
    logger.info("MES AI server shutting down")
    await plugin_manager.stop_all()
    event_bus.clear()
    logger.info("MES AI server stopped")


async def _get_installed_enabled_plugin_ids() -> set[str]:
    """Query the DB for plugin_config rows where installed=True AND enabled=True."""
    try:
        from mes.framework.db import async_session_factory
        from mes.framework.plugin.models import PluginConfig
        from sqlalchemy import select

        async with async_session_factory() as session:
            result = await session.execute(
                select(PluginConfig.plugin_id).where(
                    PluginConfig.installed.is_(True),
                    PluginConfig.enabled.is_(True),
                    PluginConfig.is_active.is_(True),
                )
            )
            return {row[0] for row in result.all()}
    except Exception as exc:
        logger.warning("Could not query plugin_config (DB may not be ready): %s", exc)
        return set()


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global exception handlers (MESException → standard error envelope)
    register_exception_handlers(app)

    # Include auth routes
    app.include_router(auth_router)

    # Include core module routes (Layer 1+)
    app.include_router(physical_model_router)
    app.include_router(product_def_router)
    app.include_router(uom_router)

    # Layer 2 routers
    app.include_router(production_router)
    app.include_router(wip_router)

    # Layer 3 routers
    app.include_router(material_router)
    app.include_router(data_collection_router)

    # Layer 4 routers
    app.include_router(quality_router)
    app.include_router(performance_router)
    app.include_router(genealogy_router)
    app.include_router(dispatch_router)

    # Integration adapter routes (P4)
    app.include_router(erp_queue_router)

    # Plugin management routes
    app.include_router(plugin_router)

    # Dashboard aggregation routes
    app.include_router(dashboard_router)

    # Real-time event WebSocket gateway
    app.include_router(events_router)

    @app.get("/health", tags=["System"])
    async def health_check():
        """Basic health check endpoint."""
        adapter_health = await plugin_manager.adapter_health()
        return {
            "status": "ok",
            "version": settings.VERSION,
            "auth_mode": settings.AUTH_MODE,
            "event_bus": settings.EVENT_BUS_TYPE,
            "plugins_loaded": len(plugin_manager.plugins),
            "adapters": adapter_health,
        }

    return app


app = create_app()
