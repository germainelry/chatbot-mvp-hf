"""
Database migration script for multi-tenant architecture.
Creates new tables and adds tenant_id columns to existing tables.
"""
from app.database import Base, SessionLocal, engine
from app.models import (
    Conversation,
    DatabaseConnection,
    Feedback,
    KnowledgeBase,
    KnowledgeBaseSource,
    Message,
    Metrics,
    Tenant,
    TenantConfiguration,
)
from sqlalchemy import text


def migrate():
    """Run migration to add multi-tenant support."""
    db = SessionLocal()
    
    try:
        # Create all new tables and add columns to existing tables
        print("Creating new tables and adding columns...")
        Base.metadata.create_all(bind=engine)
        
        # Manually add tenant_id columns to existing tables if they don't exist
        from sqlalchemy import inspect as sql_inspect
        inspector = sql_inspect(engine)
        
        tables_to_update = ['conversations', 'knowledge_base', 'feedback', 'metrics', 
                           'evaluation_metrics', 'training_data', 'corrections', 
                           'agent_actions', 'model_versions', 'experiments']
        
        for table_name in tables_to_update:
            if table_name in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'tenant_id' not in columns:
                    try:
                        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER"))
                        db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_tenant_id ON {table_name} (tenant_id)"))
                        db.commit()
                        print(f"[OK] Added tenant_id column to {table_name}")
                    except Exception as e:
                        print(f"[WARN] Could not add tenant_id to {table_name}: {e}")
                        db.rollback()
        
        # Add source_id to knowledge_base if it doesn't exist
        if 'knowledge_base' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('knowledge_base')]
            if 'source_id' not in columns:
                try:
                    db.execute(text("ALTER TABLE knowledge_base ADD COLUMN source_id INTEGER"))
                    db.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_base_source_id ON knowledge_base (source_id)"))
                    db.commit()
                    print("[OK] Added source_id column to knowledge_base")
                except Exception as e:
                    print(f"[WARN] Could not add source_id to knowledge_base: {e}")
                    db.rollback()
        
        # Check if default tenant exists
        default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        
        if not default_tenant:
            # Create default tenant
            print("Creating default tenant...")
            default_tenant = Tenant(
                name="Default Tenant",
                slug="default",
                is_active=1
            )
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
            print(f"[OK] Created default tenant with ID: {default_tenant.id}")
        else:
            print(f"[OK] Default tenant already exists with ID: {default_tenant.id}")
        
        # Create default configuration for default tenant
        default_config = db.query(TenantConfiguration).filter(
            TenantConfiguration.tenant_id == default_tenant.id
        ).first()
        
        if not default_config:
            print("Creating default tenant configuration...")
            default_config = TenantConfiguration(
                tenant_id=default_tenant.id,
                llm_provider="ollama",
                llm_model_name="llama3.2",
                embedding_model="all-MiniLM-L6-v2",
                tone="professional",
                auto_send_threshold=0.65
            )
            db.add(default_config)
            db.commit()
            print("[OK] Created default tenant configuration")
        
        # Migrate existing data to default tenant
        print("Migrating existing data to default tenant...")
        
        # Update conversations
        try:
            db.execute(
                text("UPDATE conversations SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
                {"tenant_id": default_tenant.id}
            )
            db.commit()
            print("[OK] Migrated conversations")
        except Exception as e:
            print(f"[WARN] Conversations migration: {e}")
            db.rollback()
        
        # Update messages (via conversations)
        # Messages don't have tenant_id directly, they inherit from conversations
        
        # Update knowledge base
        try:
            db.execute(
                text("UPDATE knowledge_base SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
                {"tenant_id": default_tenant.id}
            )
            db.commit()
            print("[OK] Migrated knowledge base")
        except Exception as e:
            print(f"[WARN] Knowledge base migration: {e}")
            db.rollback()
        
        # Update feedback
        try:
            db.execute(
                text("UPDATE feedback SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
                {"tenant_id": default_tenant.id}
            )
            db.commit()
            print("[OK] Migrated feedback")
        except Exception as e:
            print(f"[WARN] Feedback migration: {e}")
            db.rollback()
        
        # Update metrics
        try:
            db.execute(
                text("UPDATE metrics SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
                {"tenant_id": default_tenant.id}
            )
            db.commit()
            print("[OK] Migrated metrics")
        except Exception as e:
            print(f"[WARN] Metrics migration: {e}")
            db.rollback()
        
        print("\n[OK] Migration completed successfully!")
        print(f"Default tenant ID: {default_tenant.id}")
        print(f"Default tenant slug: {default_tenant.slug}")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting multi-tenant migration...")
    migrate()

