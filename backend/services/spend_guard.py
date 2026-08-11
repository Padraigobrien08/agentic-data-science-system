"""
Per-account and global spend admission control.

The public demo runs on a fixed monthly budget with open registration, so nothing may start
an execution without first asking whether this account — and this deployment — has budget
left. See ``docs/decisions/2026-08-11-showcase-direction.md`` (S0).

**Two independent controls, deliberately.** USD ceilings are the intuitive control but they
are only meaningful when ``llm_model_prices`` is configured: ``estimate_cost_usd`` returns
``0.0`` for an unpriced model, by design, so that cost *budgets* never bind on invented
numbers. That design is right for a budget and wrong for an abuse guard — an unpriced
deployment would compute $0.00 forever and the ceiling would never fire. Run-count ceilings
are therefore the real backstop: they are always enforceable and never depend on operator
pricing config. :func:`pricing_is_configured` exists so callers (health, startup) can say out
loud when the USD half is inert.

Costs are computed from :mod:`backend.llm.pricing` — the same table the agentic loop charges
its own ``LoopBudget.max_cost_usd`` against — rather than from
``backend.schemas.llm_usage.aggregate_llm_usage_for_calls``, which reads a *separate* settings
key (``agent_llm_pricing_json``) with different field names. Using one source keeps the
per-investigation budget and the per-account cap in agreement instead of drifting apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.llm.pricing import estimate_cost_usd, parse_model_prices
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, UserAccessTier
from backend.models.model_call import ModelCall
from backend.models.user import User

log = structlog.get_logger(__name__)

ENGINE_EDGAR = "edgar"
ENGINE_AGENTIC = "agentic"


class SpendLimitExceeded(Exception):
    """
    This run would exceed a configured ceiling.

    Carries a caller-safe ``message`` (shown to the user) and a ``scope`` of ``account`` or
    ``global`` so the API can distinguish "you are out of budget" from "the demo is out of
    budget" — a distinction that matters to a visitor, who can do nothing about the latter.
    """

    def __init__(self, message: str, *, scope: str, limit_name: str) -> None:
        self.scope = scope
        self.limit_name = limit_name
        super().__init__(message)


class EngineNotEntitled(Exception):
    """The user's tier does not permit the requested execution engine."""

    def __init__(self, message: str, *, tier: UserAccessTier) -> None:
        self.tier = tier
        super().__init__(message)


@dataclass(frozen=True)
class UsageSnapshot:
    """Runs started and estimated model spend for some scope."""

    run_count: int
    cost_usd: float
    #: False when no model prices are configured, meaning ``cost_usd`` is structurally 0.0
    #: and must not be read as "this cost nothing".
    cost_priced: bool


@dataclass(frozen=True)
class TierLimits:
    max_runs: int
    max_spend_usd: float


def pricing_is_configured(settings: Settings | None = None) -> bool:
    """True when USD ceilings can actually bind."""
    s = settings if settings is not None else get_settings()
    return bool(parse_model_prices(s.llm_model_prices))


def limits_for_tier(tier: UserAccessTier, settings: Settings) -> TierLimits:
    if tier is UserAccessTier.adaptive:
        return TierLimits(
            max_runs=settings.adaptive_max_runs_per_account,
            max_spend_usd=settings.adaptive_max_spend_usd_per_account,
        )
    if tier is UserAccessTier.guest:
        return TierLimits(max_runs=settings.guest_max_runs_per_account, max_spend_usd=0.0)
    return TierLimits(max_runs=settings.standard_max_runs_per_account, max_spend_usd=0.0)


def _spend_usd(db: Session, settings: Settings, *, run_ids_subquery) -> tuple[float, bool]:
    """Sum estimated USD over model calls belonging to the given runs."""
    prices = parse_model_prices(settings.llm_model_prices)
    if not prices:
        return 0.0, False
    rows = db.execute(
        select(
            ModelCall.model_name,
            func.coalesce(func.sum(ModelCall.prompt_tokens), 0),
            func.coalesce(func.sum(ModelCall.completion_tokens), 0),
        )
        .where(ModelCall.analysis_run_id.in_(run_ids_subquery))
        .group_by(ModelCall.model_name)
    ).all()
    total = 0.0
    for model_name, prompt_tokens, completion_tokens in rows:
        total += estimate_cost_usd(
            prices,
            model=str(model_name or ""),
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
        )
    return total, True


#: A run only consumes budget once it leaves ``pending`` — creating rows costs nothing, so
#: counting them would let a user exhaust their own allowance without spending a cent, and
#: would make the ceiling a self-inflicted denial of service rather than a cost control.
_BILLABLE = AnalysisRun.status != AnalysisRunStatus.pending


def account_usage(db: Session, user_id: UUID, *, settings: Settings | None = None) -> UsageSnapshot:
    """Lifetime billable runs and estimated spend for one account."""
    s = settings if settings is not None else get_settings()
    run_ids = select(AnalysisRun.id).where(
        AnalysisRun.initiated_by_user_id == user_id,
        _BILLABLE,
    )
    run_count = int(db.scalar(select(func.count()).select_from(run_ids.subquery())) or 0)
    cost, priced = _spend_usd(db, s, run_ids_subquery=run_ids)
    return UsageSnapshot(run_count=run_count, cost_usd=cost, cost_priced=priced)


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def global_usage_this_month(
    db: Session,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> UsageSnapshot:
    """Runs and estimated spend across every user in the current calendar month."""
    s = settings if settings is not None else get_settings()
    since = _month_start(now or datetime.now(timezone.utc))
    run_ids = select(AnalysisRun.id).where(AnalysisRun.created_at >= since, _BILLABLE)
    run_count = int(db.scalar(select(func.count()).select_from(run_ids.subquery())) or 0)
    cost, priced = _spend_usd(db, s, run_ids_subquery=run_ids)
    return UsageSnapshot(run_count=run_count, cost_usd=cost, cost_priced=priced)


def resolve_engine_for_user(
    user: User,
    requested_engine: str,
    *,
    settings: Settings | None = None,
) -> str:
    """
    The engine this user is permitted to run, given what the run asked for.

    Downgrade is silent and deliberate: a guest who somehow submits ``engine: agentic`` gets
    the deterministic chain rather than an error, because the tier is a budget decision and a
    working cheap answer serves the visitor better than a refusal. An *explicit* request from
    an authenticated non-guest is refused instead, so an account holder is never quietly
    charged-down without knowing why — see :func:`assert_engine_entitled`.
    """
    s = settings if settings is not None else get_settings()
    if not s.agentic_engine_enabled:
        return ENGINE_EDGAR
    if requested_engine != ENGINE_AGENTIC:
        return ENGINE_EDGAR
    if user.access_tier is UserAccessTier.adaptive:
        return ENGINE_AGENTIC
    return ENGINE_EDGAR


def assert_engine_entitled(
    user: User,
    requested_engine: str,
    *,
    settings: Settings | None = None,
) -> None:
    """Raise when a non-guest explicitly asked for an engine their tier does not cover."""
    s = settings if settings is not None else get_settings()
    if requested_engine != ENGINE_AGENTIC:
        return
    if user.access_tier is UserAccessTier.adaptive:
        return
    if user.access_tier is UserAccessTier.guest:
        return  # silently downgraded; see resolve_engine_for_user
    if not s.agentic_engine_enabled:
        raise EngineNotEntitled(
            "The agentic investigation engine is not enabled on this deployment.",
            tier=user.access_tier,
        )
    raise EngineNotEntitled(
        "The agentic investigation engine requires an invite code. "
        "Your account can run the deterministic analysis engine.",
        tier=user.access_tier,
    )


def check_run_admission(
    db: Session,
    user: User,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> None:
    """
    Gate one about-to-start run. Raises :class:`SpendLimitExceeded` when a ceiling is hit.

    Call before transitioning a run to ``queued``/``running`` — refusing after the work has
    started spends the money the guard exists to protect.

    Admins are exempt: the operator must always be able to run the thing they are paying for,
    including to reproduce a limit report.
    """
    s = settings if settings is not None else get_settings()
    if user.is_admin:
        return

    global_usage = global_usage_this_month(db, settings=s, now=now)
    if s.global_monthly_max_runs and global_usage.run_count >= s.global_monthly_max_runs:
        raise SpendLimitExceeded(
            "The demo has reached its monthly run limit. Explore the recorded investigations instead.",
            scope="global",
            limit_name="global_monthly_max_runs",
        )
    if (
        s.global_monthly_max_spend_usd
        and global_usage.cost_priced
        and global_usage.cost_usd >= s.global_monthly_max_spend_usd
    ):
        raise SpendLimitExceeded(
            "The demo has reached its monthly budget. Explore the recorded investigations instead.",
            scope="global",
            limit_name="global_monthly_max_spend_usd",
        )

    limits = limits_for_tier(user.access_tier, s)
    usage = account_usage(db, user.id, settings=s)
    if limits.max_runs and usage.run_count >= limits.max_runs:
        raise SpendLimitExceeded(
            f"This account has used its {limits.max_runs} available runs.",
            scope="account",
            limit_name="max_runs_per_account",
        )
    if limits.max_spend_usd and usage.cost_priced and usage.cost_usd >= limits.max_spend_usd:
        raise SpendLimitExceeded(
            "This account has reached its model spend allowance.",
            scope="account",
            limit_name="max_spend_usd_per_account",
        )


def log_spend_guard_posture(settings: Settings | None = None) -> None:
    """
    Say once, at startup, whether the guard is actually armed.

    A deployment with the agentic engine on, an invite code set, and no pricing configured has
    a USD ceiling that cannot fire. That is precisely the configuration that quietly overspends,
    so it must be visible in the logs rather than inferred from a missing metric.
    """
    s = settings if settings is not None else get_settings()
    priced = pricing_is_configured(s)
    invite_enabled = s.adaptive_invite_code is not None and bool(
        s.adaptive_invite_code.get_secret_value().strip()
    )
    log.info(
        "spend_guard_posture",
        agentic_engine_enabled=s.agentic_engine_enabled,
        adaptive_invite_enabled=invite_enabled,
        pricing_configured=priced,
        usd_ceilings_effective=priced,
        global_monthly_max_runs=s.global_monthly_max_runs,
        global_monthly_max_spend_usd=s.global_monthly_max_spend_usd,
    )
    if s.agentic_engine_enabled and invite_enabled and not priced:
        log.warning(
            "spend_guard_usd_ceilings_inert",
            hint=(
                "EDGAR_BACKEND_LLM_MODEL_PRICES is unset, so every model call estimates at "
                "$0.00 and all USD ceilings are unenforceable. Run-count ceilings still apply."
            ),
        )
