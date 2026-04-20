Steps:
0. Install Flask and mysql/pymysql (using pip)
1. Start your mysql database server.
2. Start your apache server.
3. Go to your browser and type "127.0.0.1" in the address bar and click on phyMyAdmin.
4. Create a new database named 'blog'
5. Download flask_demo.zip file from course site and unzip it.
6. There are three examples. The first two are self-explantory. Play with them
6. For example3. Import tables.sql file in blog database. It will create two tables named 'user' and 'blog_post'.
8. Run init1.py file using "python init1.py" command from the terminal.
  If you used a root password for your mysql database, edit the init1.py file to
  write that password in conn = mysql.connector.connect(host='localhost',
                       user='root',
                       password='',
                       database='blog') line.


9. Now create another tab in your browser, type "127.0.0.1:5000" in the address bar.
You should be able to see a web page with login and register links.
10. Now play with it. Look changes in the database tables.

