"""Initial database schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User Profile
    op.create_table(
        'users_profile',
        sa.Column('user_id', sa.String(255), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('business_context', sa.Text(), nullable=True),
        sa.Column('persona', sa.String(50), server_default='solopreneur'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # User Executive Agent
    op.create_table(
        'user_executive_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('agent_name', sa.String(255), server_default='Executive Agent'),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_executive_agents_user_id', 'user_executive_agents', ['user_id'])
    op.create_unique_constraint('uq_user_agent', 'user_executive_agents', ['user_id'])

    # Sessions
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('app_name', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_sessions_app_user', 'sessions', ['app_name', 'user_id'])
    op.create_index('ix_sessions_session_id', 'sessions', ['session_id'])

    # Session Events
    op.create_table(
        'session_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_index', sa.Integer(), nullable=False),
        sa.Column('event_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_session_events_session', 'session_events', ['session_id', 'event_index'])
    op.create_foreign_key('fk_session_events_session', 'session_events', 'sessions', ['session_id'])

    # Session Version History
    op.create_table(
        'session_version_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('state_diff', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_version_history_session', 'session_version_history', ['session_id', 'version'])
    op.create_foreign_key('fk_version_history_session', 'session_version_history', 'sessions', ['session_id'])

    # Initiative Templates
    op.create_table(
        'initiative_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('phases', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('default_priority', sa.String(20), server_default='medium'),
        sa.Column('persona', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Initiatives
    op.create_table(
        'initiatives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('phase', sa.String(50), server_default='ideation'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_initiatives_user', 'initiatives', ['user_id'])

    # User Journeys
    op.create_table(
        'user_journeys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stages', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('kpis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_journeys_user', 'user_journeys', ['user_id'])

    # Workflow Templates
    op.create_table(
        'workflow_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('phases', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_unique_constraint('uq_workflow_template_name', 'workflow_templates', ['name'])

    # Workflow Executions
    op.create_table(
        'workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('current_phase', sa.String(100), nullable=True),
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_workflow_executions_user', 'workflow_executions', ['user_id'])
    op.create_index('ix_workflow_executions_template', 'workflow_executions', ['template_id'])

    # Workflow Steps
    op.create_table(
        'workflow_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_workflow_steps_execution', 'workflow_steps', ['execution_id'])
    op.create_foreign_key('fk_workflow_steps_execution', 'workflow_steps', 'workflow_executions', ['execution_id'])

    # Approval Requests
    op.create_table(
        'approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), server_default='PENDING'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_approval_requests_user', 'approval_requests', ['user_id'])
    op.create_index('ix_approval_requests_token', 'approval_requests', ['token'])
    op.create_unique_constraint('uq_approval_token', 'approval_requests', ['token'])

    # Vault Documents
    op.create_table(
        'vault_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_vault_documents_user', 'vault_documents', ['user_id'])

    # Embeddings
    op.create_table(
        'embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_embeddings_document', 'embeddings', ['document_id'])
    op.create_foreign_key('fk_embeddings_document', 'embeddings', 'vault_documents', ['document_id'])

    # Agent Google Docs
    op.create_table(
        'agent_google_docs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('google_doc_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('document_url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_agent_google_docs_user', 'agent_google_docs', ['user_id'])

    # Media Assets
    op.create_table(
        'media_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('storage_path', sa.String(1000), nullable=True),
        sa.Column('public_url', sa.String(1000), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_media_assets_user', 'media_assets', ['user_id'])

    # Landing Pages
    op.create_table(
        'landing_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('react_content', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), server_default='{}'),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('published_url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_landing_pages_user', 'landing_pages', ['user_id'])
    op.create_index('ix_landing_pages_status', 'landing_pages', ['status'])

    # Landing Forms
    op.create_table(
        'landing_forms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_landing_forms_page', 'landing_forms', ['page_id'])

    # Form Submissions
    op.create_table(
        'form_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('form_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), server_default='{}'),
        sa.Column('email_sent', sa.Boolean(), server_default='false'),
        sa.Column('crm_synced', sa.Boolean(), server_default='false'),
        sa.Column('crm_contact_id', sa.String(255), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_form_submissions_form', 'form_submissions', ['form_id'])
    op.create_index('ix_form_submissions_user', 'form_submissions', ['user_id'])

    # Departments
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), server_default='IDLE'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_departments_user', 'departments', ['user_id'])

    # Products
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_products_user', 'products', ['user_id'])

    # Inventory
    op.create_table(
        'inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='0'),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_inventory_product', 'inventory', ['product_id'])

    # Orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('total_amount', sa.Float(), server_default='0'),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_orders_user', 'orders', ['user_id'])

    # Order Items
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('unit_price', sa.Float(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_order_items_order', 'order_items', ['order_id'])

    # Invoices
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_invoices_order', 'invoices', ['order_id'])

    # Connected Accounts
    op.create_table(
        'connected_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_account_id', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_connected_accounts_user', 'connected_accounts', ['user_id'])
    op.create_unique_constraint('uq_provider_account', 'connected_accounts', ['provider', 'provider_account_id'])

    # Agents
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_agents_user', 'agents', ['user_id'])

    # Skills
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('knowledge', sa.Text(), nullable=True),
        sa.Column('is_global', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_skills_user', 'skills', ['user_id'])
    op.create_unique_constraint('uq_skill_name_user', 'skills', ['name', 'user_id'])

    # User Configurations
    op.create_table(
        'user_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_configurations_user', 'user_configurations', ['user_id'])
    op.create_unique_constraint('uq_user_config_key', 'user_configurations', ['user_id', 'key'])

    # User Reports
    op.create_table(
        'user_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('report_type', sa.String(100), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_user_reports_user', 'user_reports', ['user_id'])

    # MCP Audit Logs
    op.create_table(
        'mcp_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('tool_name', sa.String(255), nullable=False),
        sa.Column('agent_name', sa.String(255), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('query_sanitized', sa.Text(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('response_status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.create_index('ix_mcp_audit_logs_user', 'mcp_audit_logs', ['user_id'])
    op.create_index('ix_mcp_audit_logs_tool', 'mcp_audit_logs', ['tool_name'])
    op.create_index('ix_mcp_audit_logs_timestamp', 'mcp_audit_logs', ['timestamp'])

    # Agent Knowledge
    op.create_table(
        'agent_knowledge',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('knowledge_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_agent_knowledge_user', 'agent_knowledge', ['user_id'])
    op.create_index('ix_agent_knowledge_type', 'agent_knowledge', ['knowledge_type'])

    # AI Jobs
    op.create_table(
        'ai_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_ai_jobs_user', 'ai_jobs', ['user_id'])
    op.create_index('ix_ai_jobs_status', 'ai_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('ai_jobs')
    op.drop_table('agent_knowledge')
    op.drop_table('mcp_audit_logs')
    op.drop_table('user_reports')
    op.drop_table('user_configurations')
    op.drop_table('skills')
    op.drop_table('agents')
    op.drop_table('connected_accounts')
    op.drop_table('invoices')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('inventory')
    op.drop_table('products')
    op.drop_table('departments')
    op.drop_table('form_submissions')
    op.drop_table('landing_forms')
    op.drop_table('landing_pages')
    op.drop_table('media_assets')
    op.drop_table('agent_google_docs')
    op.drop_table('embeddings')
    op.drop_table('vault_documents')
    op.drop_table('approval_requests')
    op.drop_table('workflow_steps')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_templates')
    op.drop_table('user_journeys')
    op.drop_table('initiatives')
    op.drop_table('initiative_templates')
    op.drop_table('session_version_history')
    op.drop_table('session_events')
    op.drop_table('sessions')
    op.drop_table('user_executive_agents')
    op.drop_table('users_profile')
