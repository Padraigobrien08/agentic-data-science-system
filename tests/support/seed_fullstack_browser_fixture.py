"""Seed a deterministic admin/project/run/artifact fixture for browser CI."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

import backend.models  # noqa: F401
from backend.db.session import SessionLocal
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, ArtifactKind, RunStepStatus
from backend.models.project import Project
from backend.models.run_step import RunStep
from backend.models.user import User
from backend.security.passwords import hash_password
from backend.services.artifact_service import ArtifactService

DEFAULT_ADMIN_EMAIL = "smoke-admin@example.com"
DEFAULT_ADMIN_PASSWORD = "Smokepass12!"
ARTIFACT_MARKER = "Seeded artifact content for CI browser test."


def _upsert_admin(session) -> User:
  email = os.environ.get("EDGAR_SMOKE_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip()
  password = os.environ.get("EDGAR_SMOKE_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
  user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
  if user is None:
    user = User(email=email)
    session.add(user)
    session.flush()

  user.display_name = "Smoke Admin"
  user.is_active = True
  user.is_admin = True
  user.hashed_password = hash_password(password)
  session.flush()
  return user


def seed_fixture() -> dict[str, str]:
  db = SessionLocal()
  try:
    now = datetime.now(timezone.utc)
    admin = _upsert_admin(db)

    project = Project(
      owner_user_id=admin.id,
      name=f"CI Browser Fixture {uuid4().hex[:8]}",
      description="Deterministic browser fixture for the full-stack workflow.",
      tickers=["MSFT"],
    )
    db.add(project)
    db.flush()

    run = AnalysisRun(
      project_id=project.id,
      initiated_by_user_id=admin.id,
      status=AnalysisRunStatus.success,
      orchestration_goal_text="Validate seeded browser run flows",
      input_payload_json={
        "tickers": ["MSFT"],
        "analysis_goal": "Review the deterministic browser fixture run.",
      },
      output_payload_json={
        "status": "success",
        "message": "Seeded full-stack browser fixture is ready.",
        "final_summary": "Seeded browser fixture final summary.",
        "user_facing_report": {
          "markdown": "# Seeded browser fixture report\n\nSeeded browser fixture takeaway.\n",
          "key_takeaways": ["Seeded browser fixture takeaway."],
          "model_call_id": None,
        },
      },
      meta_json={"seeded_fixture": True},
      started_at=now,
      finished_at=now,
    )
    db.add(run)
    db.flush()

    step = RunStep(
      analysis_run_id=run.id,
      step_index=0,
      status=RunStepStatus.success,
      label="Seed browser report artifact",
      planned_tool_name="seed_fullstack_browser_fixture",
      detail="Creates a deterministic report artifact for Playwright verification.",
      planner_tool_input_json={"seeded": True},
      meta_json={"seeded_fixture": True},
      started_at=now,
      finished_at=now,
    )
    db.add(step)
    db.flush()

    artifact = ArtifactService(db).save_bytes(
      (
        "# Seeded browser fixture report\n\n"
        "Seeded browser fixture takeaway.\n\n"
        f"{ARTIFACT_MARKER}\n"
      ).encode("utf-8"),
      role_key="report_md",
      analysis_run_id=run.id,
      run_step_id=step.id,
      filename_suffix=".md",
      mime_type="text/markdown",
      kind=ArtifactKind.document,
      meta_json={"seeded_fixture": True},
    )

    db.commit()
    return {
      "admin_email": admin.email,
      "admin_password": os.environ.get("EDGAR_SMOKE_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
      "project_id": str(project.id),
      "run_id": str(run.id),
      "artifact_id": str(artifact.id),
    }
  finally:
    db.close()


if __name__ == "__main__":
  print(json.dumps(seed_fixture()))
