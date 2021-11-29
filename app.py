import sqlite3
from datetime import datetime
from math import ceil
from os import remove

from flask import (Flask, flash, redirect, render_template, request,
                   send_from_directory, session, url_for)

from check import checkFile, checkRoll
from database.delete import deleteResultsTable
from database.heplers import parseTableName
from database.insert import insertNewCSV
from database.query import (getBranchName, getMarks, getName, getResultsList,
                            getResultsListCount, getResultsPageNavList,
                            getTableName)

app = Flask(__name__)
# TODO: Change this in production
app.config['SECRET_KEY'] = '6d5843bbf5bdc0f249376717e6d32919715b4bd02b89'


@app.route('/')
@app.route('/home')
def home():
    con = sqlite3.connect('results.db')
    page = request.args.get('page', 1, type=int)

    perPage = 14

    totalResults = getResultsListCount(con)
    pages = ceil(totalResults / perPage)
    resultsList = getResultsList(con, page, perPage)
    navList = getResultsPageNavList(con, perPage, page)

    prevUrl = url_for('home', page=page-1) if page > 1 else None
    nextUrl = url_for('home', page=page+1) if page < pages else None

    return render_template('home.html', resultsList=resultsList, page=page,
                           prevUrl=prevUrl, nextUrl=nextUrl, navList=navList)


@app.route('/roll/<table>')
def roll(table):
    bgImage = '/static/images/caps.jpg'
    return render_template('roll.html', table=table, bgImage=bgImage)


@app.route('/results')
def results():
    rollno = request.args.get('roll').strip().upper()
    table = request.args.get('table').strip()

    con = sqlite3.connect('results.db')

    try:
        if not checkRoll(rollno):
            raise Exception('Invalid rollno')
        tableName = getTableName(table, con)
        examName = parseTableName(tableName)
        marks = getMarks(con, rollno, tableName)
        name = getName(con, rollno, tableName)
        branch = getBranchName(rollno)

        if branch is None:
            branch = examName.split()[0]

        return render_template('results.html', marks=marks, name=name,
                               rollno=rollno, examName=examName, branch=branch)
    except:
        flash('Invalid Hall Ticket Number for the Exam you have selected.',
              'is-danger')
        return redirect('roll/' + table)


@app.route('/error')
def error():
    return render_template('error.html'), 400


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    bgImage = '/static/images/panel.jpg'

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(request.url)

        return render_template('admin_login.html', incorrect=True,
                               bgImage=bgImage)
    else:
        if session.get('admin'):
            examMonths = (
                'January',
                'Febraury',
                'March',
                'April',
                'May',
                'June',
                'July',
                'August',
                'September',
                'October',
                'November',
                'December'
            )
            startYear = datetime.now().year

            examYears = [year for year in range(startYear-3, startYear+6)]
            years = ['I', 'II', 'III', 'IV']
            sems = ['I', 'II']
            regulations = [f'R{i}' for i in range(10, 21)]

            error = request.args.get('error')
            success = request.args.get('success')

            return render_template('admin_panel.html', examMonths=examMonths,
                                   examYears=examYears, years=years, sems=sems,
                                   regulations=regulations, bgImage=bgImage)

        return render_template('admin_login.html', incorrect=False,
                               bgImage=bgImage)


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    bgImage = '/static/images/panel.jpg'
    con = sqlite3.connect('results.db')

    if not session.get('admin'):
        return redirect('/admin')
    elif not request.args.get('table'):
        page = request.args.get('page', 1, type=int)

        perPage = 17

        totalResults = getResultsListCount(con)
        pages = ceil(totalResults / perPage)
        resultsList = getResultsList(con, page, perPage)
        navList = getResultsPageNavList(con, perPage, page)

        prevUrl = url_for('home', page=page-1) if page > 1 else None
        nextUrl = url_for('home', page=page+1) if page < pages else None

        return render_template('admin_delete.html', resultsList=resultsList,
                               page=page, prevUrl=prevUrl, nextUrl=nextUrl,
                               navList=navList)
    else:
        tableSno = request.args.get('table')
        try:
            tableName = deleteResultsTable(con, tableSno)
            flash(f'Successfully Deleted {tableName} Results', 'is-success')
        except:
            flash('Failed to Delete', 'is-danger')
        return redirect('/delete')


@app.route('/logout')
def logout():
    if session.get('admin'):
        session.pop('admin', None)
        return redirect('/admin')
    else:
        return redirect('/')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET' or not session.get('admin'):
        return redirect('/admin')
    else:
        examMonth = request.form.get('examMonth')
        examYear = request.form.get('examYear')
        course = request.form.get('course')
        year = request.form.get('year')
        sem = request.form.get('sem')
        regulation = request.form.get('regulation').strip().upper()
        regOrSup = request.form.get('regOrSup')

        file = request.files['results']

        if not checkFile(file.filename):
            flash('Invalid File', 'is-danger')
        else:
            fileName = 'results.csv'
            file.save(fileName)

            try:
                tableName = insertNewCSV(course, year, sem, regulation, regOrSup,
                                         examMonth, examYear, fileName)
                flash(f'Successfully added {tableName} Results', 'is-success')
            except:
                flash('Results File Already Exists', 'is-danger')
            finally:
                remove(fileName)

        return redirect('/admin')


# TODO: Remove this in production
@app.route('/static/<file>')
def staticFiles(file):
    return send_from_directory(file, 'static')


if __name__ == '__main__':
    app.run(debug=True)
