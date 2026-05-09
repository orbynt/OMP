class OMPError(Exception):
    """Base exception for OMP errors."""


class InvalidOrbFile(OMPError):
    """Raised when a file does not conform to the .orb binary format."""


class VersionMismatch(OMPError):
    """Raised when a file requires a newer or incompatible protocol version."""


class UnsupportedFeature(OMPError):
    """Raised when open-tier code sees a verified-tier-only feature."""

