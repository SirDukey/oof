from flask import Flask, render_template, request, redirect, url_for
from flask_simplelogin import SimpleLogin, login_required
import pymysql
from datetime import datetime
import subprocess as sp
from flask import flash


app = Flask(__name__)

app.config['SIMPLELOGIN_USERNAME'] = 'admin'
app.config['SIMPLELOGIN_PASSWORD'] = '12345678'
SECRET_KEY = 'oV8rgcvFY1YcEWo7jXmoPQi5gaeX1J'
app.config['SECRET_KEY'] = SECRET_KEY
SimpleLogin(app)

host = 'dbserverhostname'
user = 'dbuser'
password = 'dbpass'
db = 'dbname'


def select_all():
    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=db)
    cur = conn.cursor()
    cur.execute("SELECT mailuser_id,name,email,autoresponder,autoresponder_start_date,autoresponder_end_date,autoresponder_text,autoresponder_subject "
                "FROM mail_user "
                "GROUP BY name ASC")
    result = cur.fetchall()
    yield result


def select_name(account_name):
    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=db)
    cur = conn.cursor()
    cur.execute(
        "SELECT mailuser_id,name,email,autoresponder,autoresponder_start_date,autoresponder_end_date,autoresponder_text,autoresponder_subject "
        "FROM mail_user "
        "WHERE name = '{}'".format(account_name))
    result = cur.fetchall()
    yield result


def select_text(account_name):
    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=db)
    cur = conn.cursor()
    cur.execute(
        "SELECT autoresponder_text "
        "FROM mail_user "
        "WHERE name = '{}'".format(account_name))
    result = cur.fetchall()
    yield result

def select_subject(account_name):
    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=db)
    cur = conn.cursor()
    cur.execute(
        "SELECT autoresponder_subject "
        "FROM mail_user "
        "WHERE name = '{}'".format(account_name))
    result = cur.fetchall()
    yield result

def update_insert(name,
                  auto,
                  start,
                  stop,
                  msg,
                  subj):
    conn = pymysql.connect(host=host,
                           user=user,
                           password=password,
                           db=db)
    cur = conn.cursor()
    cur.execute("UPDATE mail_user "
                "SET autoresponder = '{}', "
                "autoresponder_start_date = ('{}'), "
                "autoresponder_end_date = ('{}'), "
                "autoresponder_subject = '{}', "
                "autoresponder_text = '{}' "
                "WHERE name = '{}'".format(auto,start,stop,subj,msg,name))


def copy_file(name):
    sp.check_output(['scp',
                     'ispconfig.sieve',
                     'root@mail.novusgroup.co.za:/var/vmail/novusgroup.co.za/{}/sieve/'.format(name)])


@app.route('/', methods=['POST', 'GET'])
@login_required
def index():
    if request.method == 'POST':

        account_name = request.form['nameList']

        return redirect(url_for('account', account_name=account_name))
    else:
        return render_template('index.html',
                               select_all=select_all)


@app.route('/login')
def login():

    return render_template('login.html')


@app.route('/logout')
def logout():
    return render_template('login.html')


@app.route('/<account_name>', methods=['POST', 'GET'])
def account(account_name):
    name = account_name


    if request.method == 'POST':
        try:
            auto_checkbox = request.form['auto_checkbox']
            if auto_checkbox == 'on':
                auto = 'y'
            else:
                auto = 'n'
        except:
            auto = 'n'

        start_date = request.form['start']
        start_time = request.form['start_time']
        start = start_date + ' ' + start_time + ':00'
        stop_date = request.form['stop']
        stop_time = request.form['stop_time']
        stop = stop_date + ' ' + stop_time + ':00'
        msg = request.form['message']
        subj = request.form['subject']

        def get_days(dstart, dstop):
            date_format = '%Y-%m-%d'
            dtstart = datetime.strptime(dstart, date_format)
            dtstop = datetime.strptime(dstop, date_format)
            delta = dtstop - dtstart
            res = delta.days

            if res == 0:
                return res + 1
            elif res > 0:
                return res

        query = select_name(account_name)
        email = next(query)
        email = email[0][2]
        username = email.split('@')
        username = username[0]

        if auto == 'y':


            DAYS_VAR = get_days(start_date, stop_date)

            with open('ispconfig.sieve', 'w') as f:
                f.write("require [\"fileinto\", \"regex\", \"date\", \"relational\", \"vacation\"];\n"
                        "keep;\n"
                        "if header :contains \"X-Spam-Flag\" \"YES\" {\n"
                        "  stop;\n"
                        "}\n"
                        "if allof(currentdate :value \"ge\" \"iso8601\" \"%s\", currentdate :value \"le\" \"iso8601\" \"%s\") {\n"
                        "vacation  :days %s\n"
                        "  :subject \"%s\"\n"
                        "  :addresses [\"%s\"]\n"
                        "  \"%s\n"
                        "\";\n"
                        "}" % (start_date, stop_date, DAYS_VAR, subj, email, msg)
                        )
            copy_file(username)
            flash('Updated', 'info')
        elif auto == 'n':

            with open('ispconfig.sieve', 'w') as f:
                f.write("require [\"fileinto\", \"regex\", \"date\", \"relational\", \"vacation\"];\n"
                        "keep;"
                        )
            copy_file(username)
            flash('Updated', 'info')

        update_insert(name,
                      auto,
                      start,
                      stop,
                      msg,
                      subj)

        return redirect(url_for('account', account_name=account_name))
    else:
        return render_template('account_name.html',
                               select_all=select_all,
                               select_name=select_name(account_name),
                               select_text=select_text(account_name),
                               select_subject=select_subject(account_name))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, threaded=True, debug=True)
