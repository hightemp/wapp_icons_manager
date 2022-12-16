from flask import g, Flask, render_template, request, send_file, redirect, session, jsonify
import os
import re
import sqlite3
import glob
import re
import base64
import html

app = Flask(__name__)

DATABASE = './database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/", methods=['GET', 'POST'])
def index():
    if (request.args.get('init_db', '')=='1'):
        print("=========================================================")
        print("INIT DB")
        init_db()
        print("=========================================================")
        return redirect("/")

    sBaseURL = request.url

    sSelGroup = request.args.get('sSelGroup', '')
    sSelIcon = request.args.get('sSelIcon', '')
    sSelSavedGroup = request.args.get('sSelSavedGroup', '')
    sSelSavedIcon = request.args.get('sSelSavedIcon', '')

    if ("action" in request.args):
        print(request.args)
        if request.args["action"]=="icon_add_to_group":
            aIconsIDs = request.args.getlist("icons[]")

            for sID in aIconsIDs:
                get_db().execute("INSERT INTO save_icons_to_groups (save_group_id, icons_to_groups_id) VALUES (?, ?)", (request.args["saved-group"], sID))
            get_db().commit()
            print(aIconsIDs)

        if request.args["action"]=="icon_info":
            pass

    aGroups = query_db('SELECT * FROM groups')

    if sSelGroup=='':
        if len(aGroups)>0 and len(aGroups[0])>1:
            sSelGroup=aGroups[0][0]

    aIcons = query_db('SELECT * FROM icons_to_groups WHERE group_id=?', (sSelGroup,))

    aSavedGroups = query_db('SELECT * FROM save_groups')
    # aSavedIcons = query_db('SELECT * FROM save_icons_to_groups WHERE save_group_id=?', (sSelSavedGroup,))

    return render_template('index.html', 
        sSelGroup=sSelGroup,
        sSelIcon=sSelIcon,
        aGroups=aGroups,
        aIcons=aIcons,
        sSelSavedGroup=sSelSavedGroup,
        sSelSavedIcon=sSelSavedIcon,
        aSavedGroups=aSavedGroups
    )

@app.route("/export_to_html", methods=['GET', 'POST'])
def export_to_html():
    sSelGroup = request.args.get('sSelGroup', '')
    sSelIcon = request.args.get('sSelIcon', '')
    sSelSavedGroup = request.args.get('sSelSavedGroup', '')
    sSelSavedIcon = request.args.get('sSelSavedIcon', '')

    aSavedIcons = query_db('''
        SELECT * FROM save_icons_to_groups AS si
        LEFT JOIN icons_to_groups AS ig ON ig.id=si.icons_to_groups_id
        WHERE si.save_group_id=?
    ''', (sSelSavedGroup,))

    sHTML = ""
    for oItem in aSavedIcons:
        sHTML += '<i class="bi '+oItem[5]+'"></i>'+"\n"
    # sHTML = html.escape(sHTML)

    return render_template('export_to_html.html',
        sSelGroup=sSelGroup,
        sSelIcon=sSelIcon,
        aSavedIcons=aSavedIcons,
        sSelSavedGroup=sSelSavedGroup,
        sSelSavedIcon=sSelSavedIcon,
        sHTML=sHTML
    )

@app.route("/groups", methods=['GET', 'POST'])
def groups():
    sBaseURL = request.url

    sSelGroup = request.args.get('sSelGroup', '')
    sSelIcon = request.args.get('sSelIcon', '')
    sSelSavedGroup = request.args.get('sSelSavedGroup', '')
    sSelSavedIcon = request.args.get('sSelSavedIcon', '')

    if ("action" in request.args):
        if request.args["action"]=="accept_save_group":
            get_db().execute("INSERT INTO save_groups (name) VALUES (?)", (request.args["name"],))
            get_db().commit()
            aLastID = query_db('SELECT last_insert_rowid()')
            sSelSavedGroup = aLastID[0][0]
        if request.args["action"]=="icon_remove_group":
            get_db().execute("DELETE FROM save_groups WHERE id=?", (sSelSavedGroup,))
            get_db().execute("DELETE FROM save_icons_to_groups WHERE save_group_id=?", (sSelSavedGroup,))
            get_db().commit()
            sSelSavedGroup = ''
        if request.args["action"]=="icon_add_group":
            return render_template('group_add.html')
        if request.args["action"]=="icon_remove_from_group":
            aIconsIDs = request.args.getlist("icons[]")

            for sID in aIconsIDs:
                get_db().execute("DELETE FROM save_icons_to_groups WHERE id=?", (sID,))
            get_db().commit()
        if request.args["action"]=="icon_export":
            pass

    aGroups = query_db('SELECT * FROM groups')

    aSavedGroups = query_db('SELECT * FROM save_groups')

    if sSelSavedGroup=='':
        if len(aSavedGroups)>0 and len(aSavedGroups[0])>1:
            sSelSavedGroup=aSavedGroups[0][0]

    aSavedIcons = query_db('''
        SELECT * FROM save_icons_to_groups AS si
        LEFT JOIN icons_to_groups AS ig ON ig.id=si.icons_to_groups_id
        WHERE si.save_group_id=?
    ''', (sSelSavedGroup,))

    sCurGroup = ""
    aCurGroup = query_db('SELECT * FROM save_groups WHERE id=? LIMIT 1', (sSelSavedGroup,))
    if len(aCurGroup)>0 and len(aCurGroup[0])>1:
        sCurGroup = aCurGroup[0][1]

    aExports = [
        ["/export_to_html?sSelSavedGroup="+str(sSelSavedGroup), "Экспорт в html"]
    ]

    print(aSavedIcons)

    return render_template('groups.html', 
        sSelGroup=sSelGroup,
        sSelIcon=sSelIcon,
        aGroups=aGroups,
        sSelSavedGroup=sSelSavedGroup,
        sSelSavedIcon=sSelSavedIcon,
        aSavedGroups=aSavedGroups,
        aSavedIcons=aSavedIcons,
        sCurGroup=sCurGroup,
        aExports=aExports
    )