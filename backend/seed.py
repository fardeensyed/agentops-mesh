import sys
sys.path.insert(0, ".")
from backend.app.db import SessionLocal, init_db
from backend.app.models import User, Project
from backend.app.auth import create_api_key 
from backend.app.models import AgentConfig

init_db()
db = SessionLocal()

user = User(email="fardeen@test.com", name="Fardeen")
db.add(user)
db.commit()
db.refresh(user)

project = Project(name="AgentOps Demo Project", owner_id=user.id)
db.add(project)
db.commit()
db.refresh(project)

RAW_KEY = "agentops-test-key-real-123"
key = create_api_key(db, project.id, RAW_KEY, name="dev key")

print(f"User created:    {user.id}")
print(f"Project created: {project.id}")
print(f"Raw API key (use this in SDK): {RAW_KEY}")
print(f"Stored hash:      {key.key_hash}")

db.close()

config = AgentConfig(
    project_id=project.id,
    agent_name="default",
    spend_limit_usd=10.00,  # $10/day limit for testing
)
db.add(config)
db.commit()
print(f"Spend limit set: ${config.spend_limit_usd}/day")