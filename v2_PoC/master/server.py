import uuid
import secrets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = "sqlite+aiosqlite:///./nodes.db"
metadata = MetaData()

nodes_table = Table(
    "nodes",
    metadata,
    Column("id", String, primary_key=True),
    Column("secret_token", String),
    Column("luks_key_encrypted", String, nullable=True),
)

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)

app = FastAPI()

class NodeRegistrationResponse(BaseModel):
    node_id: str
    secret_token: str

class LuksKeyResponse(BaseModel):
    luks_key: str

class AuthRequest(BaseModel):
    node_id: str
    secret_token: str

@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

@app.post("/register", response_model=NodeRegistrationResponse)
async def register_node():
    node_id = str(uuid.uuid4())
    secret_token = secrets.token_urlsafe(32)
    print(f"Registering node {node_id} with token {secret_token}")
    async with AsyncSessionLocal() as session:
        await session.execute(
            nodes_table.insert().values(id=node_id, secret_token=secret_token)
        )
        await session.commit()
    return NodeRegistrationResponse(node_id=node_id, secret_token=secret_token)

@app.post("/init-luks", response_model=LuksKeyResponse)
async def init_luks(req: AuthRequest):
    node_id = req.node_id
    secret_token = req.secret_token

    async with AsyncSessionLocal() as session:
        result = await session.execute(nodes_table.select().where(nodes_table.c.id == node_id))
        node = result.fetchone()
        if not node or node.secret_token != secret_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Generate the LUKS key if not already present
        luks_key = secrets.token_hex(32)  # 256-bit hex key
        await session.execute(
            nodes_table.update().where(nodes_table.c.id == node_id).values(luks_key_encrypted=luks_key)
        )
        await session.commit()
    return LuksKeyResponse(luks_key=luks_key)

@app.post("/get-key", response_model=LuksKeyResponse)
async def get_key(req: AuthRequest):
    node_id = req.node_id
    secret_token = req.secret_token

    async with AsyncSessionLocal() as session:
        result = await session.execute(nodes_table.select().where(nodes_table.c.id == node_id))
        node = result.fetchone()
        if not node or node.secret_token != secret_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not node.luks_key_encrypted:
            raise HTTPException(status_code=404, detail="LUKS key not found")

        return LuksKeyResponse(luks_key=node.luks_key_encrypted)

@app.post("/run-secure-code")
async def run_secure_code(req: AuthRequest):
    node_id = req.node_id
    secret_token = req.secret_token

    async with AsyncSessionLocal() as session:
        result = await session.execute(nodes_table.select().where(nodes_table.c.id == node_id))
        node = result.fetchone()
        if not node or node.secret_token != secret_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Send a specific text file (for now plain text)
        file_path = "./secure_file.txt"  # You can replace with the actual path to the file
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        with open(file_path, "r") as file:
            content = file.read()

        return {"file_content": content}

