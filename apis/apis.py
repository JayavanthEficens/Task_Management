from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from schemas.schemas import TaskCreate, TaskResponse, UserCreate, UserResponse, UserLogin
from models.models import Task, User
from base import SessionLocal, engine
from scripts.prompt import get_Query
from auth.auth import create_token, decode_token
from typing import Annotated

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login/", tags=["Autherization"])
def user_login(user : UserLogin, db : Session = Depends(get_db)):
    user_isexist = db.query(User).filter(User.email == user.email).first()
    if not user_isexist or not user.password == user_isexist.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    data = {
        "usermail" : user.email,
        "role" : user_isexist.role,
        "id" : user_isexist.user_id
    }
    encoded_jwt = create_token(data)
    return {"token" : encoded_jwt}

@router.post("/get-Query/", tags=["Query"])
def get_query(user_prompt: str, db: Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin", "User"]
    if list[0] in roles:
        try:
            message = get_Query(user_prompt)
            result = db.execute(text(message))
            rows = result.fetchall()
            column_names = result.keys()
            output = [dict(zip(column_names, row)) for row in rows]
            return {"message": message, "data": output}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.get("/users/", response_model=list[UserResponse], tags=["Users"])
def get_users(db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin", "User"]
    if list[0] in roles:
        return db.query(User).all()
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.post("/users/", response_model=UserResponse, tags=["Users"])
def create_user(user : UserCreate, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        new_user = User(username = user.username, email = user.email, password = user.password, role = user.role)
        new_user.createdBy = list[1]
        db.add(new_user)
        try:
            db.commit()
            db.refresh(new_user)
            return new_user
        except Exception as e:
            db.rollback()
            print(e)
            raise HTTPException(status_code=400)
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_user.username = user.username
        existing_user.email = user.email
        existing_user.password = user.password
        existing_user.role = user.role
        existing_user.createdBy = list[1]
        db.commit()
        db.refresh(existing_user)
        return existing_user
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.delete("/users/{user_id}", response_model=dict, tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.get("/tasks/", response_model=list[TaskResponse], tags = ["Tasks"])
def get_tasks(db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin", "User"]
    if list[0] in roles:
        return db.query(Task).all()
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.post("/tasks/", response_model=TaskResponse, tags = ["Tasks"])
def create_task(task : TaskCreate, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        new_task = Task(todo=task.todo, status=task.status, user_id = task.user_id)
        db.add(new_task)
        try:
            db.commit()
            db.refresh(new_task)
            return new_task
        except Exception as e:
            db.rollback()
            print(e)
            raise HTTPException(status_code=400)
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.put("/tasks/{task_id}", response_model=TaskResponse, tags = ["Tasks"])
def update_task(task_id : int, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        new_task = db.query(Task).filter(task_id == Task.task_id).first()
        if not new_task:
            raise HTTPException(status_code=404, detail="Task not found")
        if new_task.status == "Completed":
            new_task.status = "Pending"
        elif new_task.status == "Pending":
            new_task.status = "Completed"
        db.commit()
        db.refresh(new_task)
        return new_task
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.delete("/tasks/{task_id}", response_model=dict, tags = ["Tasks"])
def delete_task(task_id : int, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        new_task = db.query(Task).filter(task_id == Task.task_id).first()
        if not new_task:
            raise HTTPException(status_code=404, detail="Task not found")
        if new_task.isExist:
            new_task.isExist = False
            db.commit()
            return {"message" : "Task deleted successfully"}
        return {"message" : "Task is already deleted"}
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.get("/user_tasks/{user_id}", tags = ["Users and Tasks"])
def get_tasks_of_user(user_id : int, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin", "User"]
    if list[0] in roles:
        stmt = (
            select(User, Task)
            .join(Task, Task.user_id == User.user_id, isouter=True)  # Use an outer join
            .filter(User.user_id == user_id)
        )
        results = db.execute(stmt).all()
        if not results:
            raise HTTPException(status_code=404, detail="User not found")
        user = results[0][0]
        tasks = [row[1] for row in results if row[1] is not None]

        # Return the response
        return {
            "user_id": user.user_id,
            "username": user.username,
            "usermail" : user.email,
            "tasks": tasks  # Empty list if no tasks are assigned
        }
    else:
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.put("/usesr_tasks_update/{user_id}", response_model = list[TaskResponse], tags = ["Users and Tasks"])
def update_tasks_of_user(user_id : int, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        task_new = db.query(Task).filter(Task.user_id == user_id).all()
        for task in task_new:
            if task.status == "Completed":
                task.status = "Pending"
            elif task.status == "Pending":
                task.status = "Completed"
            db.commit()
            db.refresh(task)
        return task_new
    else :
        raise HTTPException(status_code=450, detail="This role cannot access")

@router.delete("/user_tasks/{user_id}", response_model=dict, tags = ["Users and Tasks"])
def delete_tasks_of_user(user_id : int, db : Session = Depends(get_db), list = Depends(decode_token)):
    roles = ["Admin"]
    if list[0] in roles:
        db.query(Task).filter(user_id == Task.user_id).update({Task.isExist: False})
        db.commit()
        return {"message" : "Tasks succesfully deleted "}
    else :
        raise HTTPException(status_code=450, detail="This role cannot access")