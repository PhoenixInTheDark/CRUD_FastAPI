from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

class Contact(BaseModel):
    nickname: str
    phone: int

@app.get("/")
def index():
    return {"data": {"message": "hello world!"}}

@app.get("/comment/{id}")
def comments(id: int):
    return {"data": {"comment": id}}

@app.get("/queryParam")
def queryParam(limit: int, published: bool = True):
    if(published):
        return {"limit": f"{limit}"}
    else:
        return {"limit": f"{limit} from unpublished db"}

@app.post("/createContact")
def createContact(query: Contact):
    return {"message": f"{query.nickname}, {query.phone}"}