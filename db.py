import pymysql
from pymysql.cursors import DictCursor

class Database():
    def __init__(self):
        super().__init__()

        self.connect = pymysql.connect(
        host='localhost',
        user='root',
        password='root',
        db='DEMO_bike_shop',
        cursorclass=DictCursor)

        self.cursor = self.connect.cursor()
