from __future__ import annotations


SCHEMA_VERSION = 1


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS contract_executions (
    execution_id TEXT PRIMARY KEY,

    contract_number TEXT NOT NULL,
    dependency TEXT NOT NULL,

    contract_identity TEXT NOT NULL,
    dependency_identity TEXT NOT NULL,

    status TEXT NOT NULL,
    last_completed_step TEXT NOT NULL,
    current_step TEXT,
    last_failed_step TEXT,

    attempt_count INTEGER NOT NULL DEFAULT 0
        CHECK (attempt_count >= 0),

    portal_profile TEXT,

    last_error_code TEXT,
    last_error_category TEXT,
    last_error_message TEXT,
    last_error_retryable INTEGER,
    last_error_metadata TEXT,

    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    completed_at TEXT,

    CONSTRAINT uq_contract_execution_identity
        UNIQUE (
            contract_identity,
            dependency_identity
        )
);

CREATE INDEX IF NOT EXISTS
    idx_contract_executions_status
ON contract_executions(status);

CREATE INDEX IF NOT EXISTS
    idx_contract_executions_updated_at
ON contract_executions(updated_at);
"""


UPSERT_EXECUTION_SQL = """
INSERT INTO contract_executions (
    execution_id,
    contract_number,
    dependency,
    contract_identity,
    dependency_identity,
    status,
    last_completed_step,
    current_step,
    last_failed_step,
    attempt_count,
    portal_profile,
    last_error_code,
    last_error_category,
    last_error_message,
    last_error_retryable,
    last_error_metadata,
    created_at,
    started_at,
    updated_at,
    completed_at
)
VALUES (
    :execution_id,
    :contract_number,
    :dependency,
    :contract_identity,
    :dependency_identity,
    :status,
    :last_completed_step,
    :current_step,
    :last_failed_step,
    :attempt_count,
    :portal_profile,
    :last_error_code,
    :last_error_category,
    :last_error_message,
    :last_error_retryable,
    :last_error_metadata,
    :created_at,
    :started_at,
    :updated_at,
    :completed_at
)
ON CONFLICT(execution_id)
DO UPDATE SET
    contract_number = excluded.contract_number,
    dependency = excluded.dependency,
    contract_identity = excluded.contract_identity,
    dependency_identity = excluded.dependency_identity,
    status = excluded.status,
    last_completed_step = excluded.last_completed_step,
    current_step = excluded.current_step,
    last_failed_step = excluded.last_failed_step,
    attempt_count = excluded.attempt_count,
    portal_profile = excluded.portal_profile,
    last_error_code = excluded.last_error_code,
    last_error_category = excluded.last_error_category,
    last_error_message = excluded.last_error_message,
    last_error_retryable = excluded.last_error_retryable,
    last_error_metadata = excluded.last_error_metadata,
    created_at = excluded.created_at,
    started_at = excluded.started_at,
    updated_at = excluded.updated_at,
    completed_at = excluded.completed_at;
"""