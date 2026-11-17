from enum import Enum
class Role(str, Enum):
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class VersionStatus(str, Enum):
    pending = 'pending'
    canary = 'canary'
    active = 'active'
    retired = 'retired'
class Lane(str, Enum):
    active = 'active'
    canary = 'canary'
