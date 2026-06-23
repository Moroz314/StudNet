from ..database.repositories.user.auth import UserRepository
from ..database.repositories.user.profile import ProfileRepository
from ..database.core import get_db
from ..users.auth.service.utils import get_password_hash
from .fill_data import *
import random


session = next(get_db())
user_repo = UserRepository(session=session)
profile_repo = ProfileRepository(session=session)

emails = [
    "alex.ivanov1985@gmail.com",
    "maria.petrova92@yahoo.com",
    "sergio.reyes@outlook.com",
    "anna.schmidt85@hotmail.com",
    "viktor.kuznetsov@mail.ru",
    "sophie.miller@protonmail.com",
    "jack.wilson2023@icloud.com",
    "linda.chen@yandex.ru",
    "mohammed.ali@company.org",
    "elena.volkova1988@edu.uni.de"
]

def generate_users():
    for email in emails:
        password = get_password_hash("12345")
        user_data = {
            "email": email,
            "password": password
        }
        user_id = user_repo.create(user_data).id

        profile_data = {
            "user_id": user_id,
            "name": random.choice(names),
            "lastname":  random.choice(lastnames),
            "username": random.choice(usernames),
            "birth_date": random.choice(birth_dates),
            "university":  random.choice(universities),
            "faculty": random.choice(faculties),
            "course": random.choice(courses),
            "info": random.choice(infos),
            "interests": random.choice(interests_list),
            "skills": random.choice(skills_list),
            "links": random.choice(links_list)
        }

        profile_repo.create_profile(profile_data)



    print("Добавлено 10 записей!")