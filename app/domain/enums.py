from __future__ import annotations

from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    DECLINE = "DECLINE"


class Result(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    INFO = "INFO"  # informational / could-not-determine


class Action(str, Enum):
    """The evidence-gathering moves available to the agent.

    Each maps to one CAMARA API (except step_up_otp, the last-resort fallback).
    """

    NUMBER_VERIFY = "number_verify"
    SIM_SWAP = "sim_swap"
    DEVICE_SWAP = "device_swap"
    LOCATION_VERIFY = "location_verify"
    REACHABILITY = "reachability"
    ROAMING = "roaming"
    DEVICE_INTELLIGENCE = "device_intelligence"
    STEP_UP_OTP = "step_up_otp"


# Human-readable CAMARA API label for each action (rendered in the chain).
API_LABEL: dict[Action, str] = {
    Action.NUMBER_VERIFY: "Number Verification",
    Action.SIM_SWAP: "SIM Swap",
    Action.DEVICE_SWAP: "Device Swap",
    Action.LOCATION_VERIFY: "Location Verification",
    Action.REACHABILITY: "Device Reachability Status",
    Action.ROAMING: "Device Roaming Status",
    Action.DEVICE_INTELLIGENCE: "Device Intelligence",
    Action.STEP_UP_OTP: "Step-up (OTP)",
}


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"       # trust is live; signals are being watched
    REVOKED = "REVOKED"     # a mid-session SIM/device change killed it
    ENDED = "ENDED"         # ended by the caller
    EXPIRED = "EXPIRED"     # TTL reached


class Hypothesis(str, Enum):
    ACCOUNT_TAKEOVER = "account_takeover"
    MULE = "mule"
    BOT_FARM = "bot_farm"
    LEGIT = "legit"
    LEGIT_THIN_FILE = "legit_thin_file"
    # Reverse Isnad: is an inbound *caller* who they claim to be?
    IMPERSONATION = "impersonation"
