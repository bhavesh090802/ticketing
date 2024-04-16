from typing import List ,Optional

import databases
import sqlalchemy
from fastapi import FastAPI
from datetime import datetime,timedelta
from pydantic import BaseModel

# SQLAlchemy specific code
DATABASE_URL = "sqlite:///./ticket.db"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

tickets = sqlalchemy.Table(
    "tickets",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("toassign", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("ticket_priority", sqlalchemy.String),
    sqlalchemy.Column("ticket_group", sqlalchemy.String),
    sqlalchemy.Column("remark", sqlalchemy.String),
    sqlalchemy.Column("created_date", sqlalchemy.DateTime),
    sqlalchemy.Column("closing_time", sqlalchemy.DateTime),
)

agents = sqlalchemy.Table(
    "agents",
    metadata,
    sqlalchemy.Column("agent_id",sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("agent_name", sqlalchemy.String),
    sqlalchemy.Column("agent_group", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)


# tickets table

class TicketIn(BaseModel):
    email: str
    description: str
    toassign: str
    status:str
    ticket_priority: str
    ticket_group: str 
    remark: str


class Ticket(BaseModel):
    id: int
    email: str
    description: str
    toassign: str
    status:str
    ticket_priority: str
    ticket_group: str
    remark: str

# agent table
class AgentIn(BaseModel):
    agent_name: str
    agent_group: Optional[str]

class Agent(BaseModel):
    agent_id: int
    agent_name: str
    agent_group: str

app = FastAPI(title="Ticketing Management")


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# tickets

# creating ticket
@app.post("/tickets/", response_model=Ticket, tags=['Ticket Management'])
async def create_ticket(ticket: TicketIn):
    created_date = datetime.now()
    closing_time = created_date + timedelta(hours=24)
    query = tickets.insert().values(
        email=ticket.email,
        description=ticket.description,
        toassign=ticket.toassign,
        status=ticket.status,
        ticket_priority=ticket.ticket_priority,
        ticket_group=ticket.ticket_group,
        remark=ticket.remark,
        created_date=created_date,
        closing_time=closing_time,
    )
    last_record_id = await database.execute(query)
    return {**ticket.dict(), "id": last_record_id}



# fetching ticket details
@app.get("/tickets/", response_model=List[Ticket], tags=['Ticket Management'])
async def read_tickets():
    query = tickets.select()
    return await database.fetch_all(query)



# updating ticket
@app.put('/tickets/{id}',response_model=Ticket,tags=['Ticket Management'])
async def update_ticket(id:int,ticket1:TicketIn):
    query1 = tickets.update().values(
        status=ticket1.status,
        remark=ticket1.remark,
    ).where(tickets.c.id==id)

    last_record_id1 = await database.execute(query1)
    return {**ticket1.dict(), "id": last_record_id1}

# Assigning agent


@app.get("/tickets/{ticket_id}/assign/{agent_id}", tags=['Ticket Management'])
async def assign_agent_to_ticket(ticket_id: int, agent_id: int):
    # Fetch the ticket based on the provided ticket ID
    ticket_query = tickets.select().where(tickets.c.id == ticket_id)
    ticket = await database.fetch_one(ticket_query)

    if ticket:
        ticket_group = ticket["ticket_group"]

        # Fetch the agent based on the provided agent ID and same ticket group
        agent_query = agents.select().where(
            (agents.c.agent_id == agent_id) & (agents.c.agent_group == ticket_group)
        )
        agent = await database.fetch_one(agent_query)

        if agent:
            # Update the ticket with the assigned agent name
            update_query = (
                tickets.update()
                .values(toassign=agent["agent_name"])
                .where(tickets.c.id == ticket_id)
            )
            await database.execute(update_query)

            # Fetch the updated ticket
            updated_ticket_query = tickets.select().where(tickets.c.id == ticket_id)
            updated_ticket = await database.fetch_one(updated_ticket_query)

            return {
                "message": "Agent assigned to ticket successfully",
                "ticket": updated_ticket,
            }

    # If the ticket or agent is not found or they belong to different groups, return an error message
    return {"message": "Ticket or agent not found or they belong to different groups"}

# agents


# Adding Agent
@app.post("/agents/", response_model=Agent,tags=['Ticket Management'])
async def add_agents(agent: AgentIn):
    # Check if agent name already exists in the table
    query_existing_agent = agents.select().where(agents.c.agent_name == agent.agent_name)
    existing_agent = await database.fetch_one(query_existing_agent)

    if existing_agent:
        # Agent name already exists, return an error or appropriate response
        return {"message": "Agent name already exists"}

    # Insert the agent if it doesn't already exist
    agent_query1 = agents.insert().values(
        agent_name=agent.agent_name,
        agent_group=agent.agent_group,
    )
    last_record_id3 = await database.execute(agent_query1)
    return {**agent.dict(), "agent_id": last_record_id3}




# fetching agent detail
@app.get("/agents/", response_model=List[Agent], tags=['Ticket Management'])
async def read_agents():
    agent_query = agents.select()
    return await database.fetch_all(agent_query)


# /tickets/