from __future__ import annotations

from omp.exceptions import InvalidOrbFile
from omp.proto import passport_pb2


def validate_passport(passport: passport_pb2.OrbPassport) -> None:
    if not passport.protocol_metadata.protocol_name:
        raise InvalidOrbFile("protocol metadata is missing protocol_name")
    if not passport.protocol_metadata.protocol_version:
        raise InvalidOrbFile("protocol metadata is missing protocol_version")
    if not passport.identity.passport_id:
        raise InvalidOrbFile("identity is missing passport_id")
    if not passport.identity.identity_id:
        raise InvalidOrbFile("identity is missing identity_id")
    if not passport.identity.namespace_id:
        raise InvalidOrbFile("identity is missing namespace_id")
    if passport.verified:
        raise InvalidOrbFile("open-tier passports must not be marked verified")
    if passport.tier and passport.tier != "open":
        raise InvalidOrbFile("OMP currently supports open-tier passports")
