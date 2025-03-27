# WUKONG
- Our Project Title: Ticketing system for student queries
- Our Software Name: WUKONG University Ticket System
- Name of Authors:
  - Kaicheng Chen
  - Lei Ding
  - Zhaoqi He
  - Yi Lu
  - Chengang Shen
  - Sijia Xia
  - Xuyang Xiao
  - Jiangjing Xu
  - Hongyuan Zhao
- Reference List:
  - We have used ChatGPT to assist us with writing some of our automated tests. They are under "tickets/tests".
  - We have used the some of the base code from last Small Group Project for login. They are under "authentication.py".  

$ source venv/bin/activate  
$ pip install -r requirements.txt  
$ pip install "moto<4.0.0"  
$ pip install channels  
$ python manage.py migrate  
$ python manage.py makemigrations  
$ python3 manage.py seed  
$ python manage.py loaddata tickets/tests/fixtures/default_superuser.json  
$ python manage.py runserver  
$ python manage.py test tickets  
$ coverage run --source=tickets manage.py test tickets  
$ coverage html  
