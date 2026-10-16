from enum import IntEnum


class RiskLevel(IntEnum):
    """Weather risk at a point. The integer value is the score used for averaging."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


class CheckpointSpacing(IntEnum):
    """Distance in miles between weather checkpoints."""

    TEN = 10
    TWENTY_FIVE = 25
    FIFTY = 50
