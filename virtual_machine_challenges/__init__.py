from __future__ import division  # Use floating point for math calculations

import math

from flask import Blueprint,redirect

from CTFd import create_app
from CTFd.models import Challenges, Solves, db
from CTFd.plugins import register_plugin_assets_directory, register_admin_plugin_menu_bar

from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.utils.modes import get_model
from CTFd.utils.user import get_current_user, is_admin
from CTFd.utils.decorators import authed_only
import requests
import string
import random
import json
import time
from redis import Redis
import os
from rq import Worker, Queue, Connection
from datetime import timedelta

# Module Imports
import mariadb
import sys

guacamole_user="guacamole_user"
guacamole_password="test"

class VMChallengesModel(Challenges):
    __mapper_args__ = {"polymorphic_identity": "virtual_machine_challenges"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    ip = db.Column(db.String(80))
    proto = db.Column(db.String(80))
    port = db.Column(db.String(80))
    scenario_id = db.Column(db.String(80))
    time_limit = db.Column(db.Integer, default=1440)



class VMChallenge(BaseChallenge): # Name of table is this with underscores
    id = "virtual_machine_challenges"  # Unique identifier used to register challenges
    name = "virtual_machine_challenges"  # Name of a challenge type
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/virtual_machine_challenges/assets/create.html",
        "update": "/plugins/virtual_machine_challenges/assets/update.html",
        "view": "/plugins/virtual_machine_challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/virtual_machine_challenges/assets/create.js",
        "update": "/plugins/virtual_machine_challenges/assets/update.js",
        "view": "/plugins/virtual_machine_challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/virtual_machine_challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "virtual_machine_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = VMChallengesModel

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        challenge = VMChallengesModel.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "proto": challenge.proto,
            "port": challenge.port,
            "ip": challenge.ip,
            "scenario_id": challenge.scenario_id,
            "time_limit": challenge.time_limit,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
        }
        return data

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()

        for attr, value in data.items():
            setattr(challenge, attr, value)
        challenge.value=0 # THIS! This is the final chance to set this value
        db.session.commit()
        return challenge

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

def add_current_user_to_guac():
    try:
        conn = mariadb.connect(
            user=guacamole_user,
            password=guacamole_password,
            host="127.0.0.1",
            port=3306,
            database="guacamole_db",
            autocommit=True
        )

    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")

    cur = conn.cursor()
    # cur.execute('insert ignore into guacamole_entity (name,type) values (?,"USER")', (get_current_user().name,))
    cur.execute('select entity_id from guacamole_entity where name = ? and type = "USER"',
                (get_current_user().name,))
    current_results = cur.fetchone()
    if current_results is not None:
        entity_id = current_results[0]
    else:
        cur.execute('insert ignore into guacamole_entity (name,type) values (?,"USER")', (get_current_user().name,))
        entity_id = cur.lastrowid

    cur.execute('select * from guacamole_user where entity_id = ?', (entity_id,))
    current_results = cur.fetchone()
    if current_results is None:
        random_password = ''.join(
            (random.choice(string.ascii_letters + string.digits + string.punctuation) for i in range(12)))
        cur.execute('SET @salt = UNHEX(SHA2(UUID(), 256))')
        cur.execute(
            'insert ignore into guacamole_user (entity_id,password_salt,password_hash,password_date) values (?,@salt,UNHEX(SHA2(CONCAT(?, HEX(@salt)), 256)),CURRENT_TIMESTAMP)',
            (entity_id, random_password))

    cur.execute('select entity_id from guacamole_entity where name = "ctfdadmin" and type = "USER_GROUP"')
    current_results_entity = cur.fetchone()
    if current_results_entity is not None:
        ctfdadmin_entity_id = current_results_entity[0]
    cur.execute('select user_group_id from guacamole_user_group where entity_id = ?',(ctfdadmin_entity_id,))
    current_results_group_id = cur.fetchone()
    if current_results_group_id is not None:
        ctfdadmin_group_id = current_results_group_id[0]
    if current_results_group_id is None or current_results_entity is None:
        cur.execute('insert ignore into guacamole_entity (name,type) values (?,"USER_GROUP")', ("ctfdadmin",))
        ctfdadmin_entity_id = cur.lastrowid
        cur.execute('insert ignore into guacamole_user_group (entity_id) values (?)', (ctfdadmin_entity_id,))
        ctfdadmin_group_id = cur.lastrowid

    if is_admin():
        cur.execute('select user_group_id from guacamole_user_group_member where user_group_id = ? and member_entity_id = ?',(ctfdadmin_group_id,entity_id))
        current_results = cur.fetchone()
        if current_results is None:
            cur.execute('insert ignore into guacamole_user_group_member (user_group_id,member_entity_id) values (?,?)', (ctfdadmin_group_id,entity_id))
    return entity_id,ctfdadmin_entity_id

def start_status_for_user(challenge,current_user):
    scenario_id = challenge.scenario_id
    r = requests.get(
        f'{challenge.proto}://{challenge.ip}:{challenge.port}/{current_user.id}/{scenario_id}/')

    if r.status_code == 201:
        entity_id, ctfdadmin_entity_id = add_current_user_to_guac()
        try:
            conn = mariadb.connect(
                user=guacamole_user,
                password=guacamole_password,
                host="127.0.0.1",
                port=3306,
                database="guacamole_db",
                autocommit=True
            )

        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")

        cur = conn.cursor()
        cur.execute('select * from guacamole_connection_group where connection_group_name = ?',
                    (f"{scenario_id}_{current_user.name}",))
        current_results = cur.fetchone()
        if current_results is None:
            cur.execute('insert ignore into guacamole_connection_group (connection_group_name) values (?)',
                        (f"{scenario_id}_{current_user.name}",))
            connection_group = cur.lastrowid
            for c in json.loads(r.content):
                cur.execute('insert into guacamole_connection (connection_name,parent_id,protocol) values (?,?,?)',
                            (c[0], connection_group, c[3]))
                connection_id = cur.lastrowid
                cur.execute(
                    'INSERT ignore INTO guacamole_connection_parameter (connection_id,parameter_name,parameter_value) VALUES (?, ? ,?)',
                    (connection_id, 'hostname', challenge.ip))
                cur.execute(
                    'INSERT ignore INTO guacamole_connection_parameter (connection_id,parameter_name,parameter_value) VALUES (?, ? ,?)',
                    (connection_id, 'port', c[2]))
                cur.execute(
                    'insert ignore into guacamole_connection_permission (entity_id,connection_id,permission) values (?,?,"READ")',
                    (entity_id, connection_id))
                cur.execute(
                    'insert ignore into guacamole_connection_permission (entity_id,connection_id,permission) values (?,?,"READ")',
                    (ctfdadmin_entity_id, connection_id))
            cur.execute(
                'insert ignore into guacamole_connection_group_permission (entity_id,connection_group_id,permission) values (?,?,"READ")',
                (entity_id, connection_group))
            cur.execute(
                'insert ignore into guacamole_connection_group_permission (entity_id,connection_group_id,permission) values (?,?,"READ")',
                (ctfdadmin_entity_id, connection_group))

        conn.close()

        q = Queue(connection=Redis())
        q.enqueue_in(timedelta(minutes=challenge.time_limit), func=end_for_user,args=(challenge,current_user))
        return f'<a href="/guacamole/">Guacamole Access VMs {entity_id}{json.loads(r.content)}</a>', 201
    else:
        return r.content, r.status_code

def end_for_user(challenge,current_user):
    scenario_id = challenge.scenario_id
    r = requests.get(
        f'{challenge.proto}://{challenge.ip}:{challenge.port}/{current_user.id}/{scenario_id}/end')
    if r.status_code == 202:
        try:
            conn = mariadb.connect(
                user=guacamole_user,
                password=guacamole_password,
                host="127.0.0.1",
                port=3306,
                database="guacamole_db",
                autocommit=True
            )

        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")

        cur = conn.cursor()
        cur.execute('select * from guacamole_connection_group where connection_group_name = ?',
                    (f"{scenario_id}_{current_user.name}",))
        current_results = cur.fetchone()
        if current_results is not None:
            cur.execute('delete from guacamole_connection_group where connection_group_name = ?',
                        (f"{scenario_id}_{current_user.name}",))

    return r.content, r.status_code

def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["virtual_machine_challenges"] = VMChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/virtual_machine_challenges/assets/"
    )
    register_admin_plugin_menu_bar(title="Guacamole", route="/guac")

    @app.route("/vm_control/<challenge_id>")
    @authed_only
    def vm_control_start_status(challenge_id):
        challenge = VMChallengesModel.query.filter_by(id=challenge_id).first()
        return start_status_for_user(challenge,get_current_user())

    @app.route("/vm_control/<challenge_id>/end")
    @authed_only
    def vm_control_end(challenge_id):
        challenge = VMChallengesModel.query.filter_by(id=challenge_id).first()
        return end_for_user(challenge,get_current_user())

    @app.route('/guac')
    def login_to_guac():
        add_current_user_to_guac()
        return redirect('/guacamole')


    @app.route('/getusername')
    def getusername():
       return get_current_user().name

# https://docs.gunicorn.org/en/stable/deploy.html
# Set CTFd option to reverse_proxy true