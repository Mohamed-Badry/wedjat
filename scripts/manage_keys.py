"""
Manage API Keys for gr_sat Wedjat API

Usage:
  pixi run python scripts/manage_keys.py create "SvelteKit Master Key"
  pixi run python scripts/manage_keys.py list
"""
import argparse
from sqlmodel import Session, select
import sys
from pathlib import Path

# Ensure api can be imported
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.database import get_engine
from api.db_models import ApiKey

def create_key(description: str):
    engine = get_engine()
    if not engine:
        print("Error: Database not configured.")
        return

    with Session(engine) as session:
        new_key = ApiKey(description=description)
        session.add(new_key)
        session.commit()
        session.refresh(new_key)
        print(f"\n✅ Successfully created API Key!")
        print(f"Description: {new_key.description}")
        print(f"Key: {new_key.key}\n")
        print("Keep this key safe! You can pass it in the X-API-Key header.")

def list_keys():
    engine = get_engine()
    if not engine:
        print("Error: Database not configured.")
        return

    with Session(engine) as session:
        keys = session.exec(select(ApiKey)).all()
        if not keys:
            print("No API keys found.")
            return
            
        print(f"\nFound {len(keys)} API keys:\n")
        for k in keys:
            status = "🟢 Active" if k.is_active else "🔴 Inactive"
            print(f"- [{status}] {k.description} (Created: {k.created_at.strftime('%Y-%m-%d')})")
            print(f"  Key: {k.key}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage API Keys")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("description", type=str, help="Description for what this key is used for")
    
    list_parser = subparsers.add_parser("list", help="List all API keys")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_key(args.description)
    elif args.command == "list":
        list_keys()
