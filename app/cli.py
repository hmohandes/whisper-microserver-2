"""Console commands to manage API tokens stored in PostgreSQL.

Usage:
    python -m app.cli create-token --name my-client
    python -m app.cli list-tokens
    python -m app.cli revoke-token --name my-client
"""
import typer

from .auth import create_token_record
from .db import SessionLocal, init_db
from .models import ApiToken

cli = typer.Typer(help="Manage Whisper microservice API tokens.")


@cli.command("create-token")
def create_token(name: str = typer.Option(..., "--name", "-n", help="Unique client name"),
                 quota: int | None = typer.Option(None, "--quota", "-q", help="Max allowed requests")):
    init_db()
    db = SessionLocal()
    try:
        if db.query(ApiToken).filter(ApiToken.name == name).first():
            typer.echo(f"Token with name '{name}' already exists.", err=True)
            raise typer.Exit(code=1)
        record, plain = create_token_record(db, name, quota)
        typer.echo(f"Token created for '{name}' (id={record.id}).")
        typer.echo("COPY IT NOW - it cannot be retrieved again:")
        typer.echo(plain)
    finally:
        db.close()


@cli.command("list-tokens")
def list_tokens():
    init_db()
    db = SessionLocal()
    try:
        rows = db.query(ApiToken).order_by(ApiToken.id).all()
        if not rows:
            typer.echo("No tokens found.")
            return
        for r in rows:
            status = "revoked" if r.revoked else ("quota_exceeded" if (r.quota is not None and r.usage >= r.quota) else "active")
            usage_str = f"usage={r.usage}" if r.quota is not None else "usage=unlimited"
            quota_str = f"/{r.quota}" if r.quota is not None else ""
            typer.echo(f"[{r.id}] {r.name} {usage_str}{quota_str} prefix={r.prefix}... status={status} created={r.created_at} last_used={r.last_used_at}")
    finally:
        db.close()


@cli.command("revoke-token")
def revoke_token(name: str = typer.Option(..., "--name", "-n", help="Client name to revoke")):
    init_db()
    db = SessionLocal()
    try:
        rec = db.query(ApiToken).filter(ApiToken.name == name).first()
        if not rec:
            typer.echo(f"No token named '{name}'.", err=True)
            raise typer.Exit(code=1)
        rec.revoked = True
        db.commit()
        typer.echo(f"Token '{name}' revoked.")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
