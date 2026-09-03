"""Business-level helpers for application health."""


def service_status() -> str:
    """Provide a small service-layer seam for future health dependencies."""
    return "ok"
