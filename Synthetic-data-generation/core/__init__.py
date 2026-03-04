"""Core v2 architecture: canonical truth layer, provenance, and latent traits."""
from .canonical import (
    CanonicalSubject, LatentTraits, SubjectIdentity,
    SubjectTimeline as CanonicalTimeline, SubjectDisposition,
    ArmAssignment, CrossoverSequence,
    AECandidate, AEEvent, MHEvent, CMEvent, EXEvent,
    frailty_to_multiplier, MAX_FRAILTY_MULTIPLIER,
)
from .provenance import ProvenanceMap, CanonicalRelationship
