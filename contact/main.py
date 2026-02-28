from fastapi import FastAPI, Depends
from . import schemas, database, models
from sqlalchemy.orm import Session

app = FastAPI()

models.Base.metadata.create_all(database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/contact_add")
def contact_add(query: schemas.Contact, db: Session = Depends(get_db)):
    new_contact = models.Contact(nickname=query.nickname, phone=query.phone, isActive=query.isActive)
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return {"message": f"Contact {new_contact} has created"}

@app.get("/contact_getAll")
def contact_getAll(db: Session = Depends(get_db)):
    return db.query(models.Contact).all()

@app.post("/contact_get")
def contact_get(query: schemas.ContactNickname, db: Session = Depends(get_db)):
    contact_nickname = db.query(models.Contact).filter(models.Contact.nickname==query.nickname).all()
    return contact_nickname

@app.post("/contact_update")
def contact_update(query: schemas.ContactNickname, newQuery: schemas.Contact, db: Session = Depends(get_db)):
    db.query(models.Contact).filter(models.Contact.nickname == query.nickname).update({
        models.Contact.nickname: newQuery.nickname,
        models.Contact.phone: newQuery.phone,
        models.Contact.isActive: newQuery.isActive,
    })
    db.commit()
    return {"message": "Info updated"}

@app.post("/contact_delete")
def contact_delete(query: schemas.ContactNickname, db: Session = Depends(get_db)):
    db.query(models.Contact).filter(models.Contact.nickname == query.nickname).delete()
    db.commit()
    return {"message": "Info deleted"}