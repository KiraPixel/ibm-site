import os

from flask import Flask, redirect, render_template, url_for
from flask_mysqldb import MySQL
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from config import settings
from mysqlconfig import host, user, password, db_name

app = Flask(__name__)

app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = db_name
mysql = MySQL(app)

app.secret_key = "random bytes"
app.debug = True
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"

app.config["DISCORD_CLIENT_ID"] = settings['DISCORD_CLIENT_ID']
app.config["DISCORD_CLIENT_SECRET"] = settings['DISCORD_CLIENT_SECRET']
app.config["DISCORD_REDIRECT_URI"] = f"http://{settings['host']}{settings['DISCORD_REDIRECT_URI']}"
app.config["DISCORD_BOT_TOKEN"] = settings['DISCORD_BOT_TOKEN']

print(app.config["DISCORD_REDIRECT_URI"])

discord = DiscordOAuth2Session(app)


class IClient:
    def __init__(self, ClientId):
        cur = mysql.connection.cursor()
        cur.execute(f"""
            SELECT id, discordId, minecraftNick, money, deposit_box, deposit_money, 
            dateRegister, card, status, reklama, verification, clan, salesman 
            FROM user 
            WHERE id = {ClientId} or discordId = {ClientId}
        """)
        record = cur.fetchone()
        cur.close()
        if record is None:
            self.check = False
            return
        self.check = True
        self.id = record[0]
        self.discord_id = record[1]
        self.nick = record[2]
        self.money = record[3]
        self.deposit_box = record[4]
        self.deposit_money = record[5]
        self.register_date = record[6]
        self.card = record[7]
        self.status = record[8]
        self.reklama = record[9]
        self.verification = record[10]
        self.clan = record[11]
        self.salesman = record[12]


class IShop:
    def __init__(self, ClientId):
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT id, owner, managers, name, dateRegister, rating FROM shops WHERE id = {ClientId}")
        record = cur.fetchone()
        if record is None:
            self.check = False
            return
        cur.execute(f"SELECT minecraftNick FROM user WHERE id = {record[1]}")
        records = cur.fetchone()
        cur.close()
        self.check = True
        self.id = record[0]
        self.owner_id = record[1]
        self.owner_name = records[0]
        self.managers = record[2]
        self.name = record[3]
        self.dateRegister = record[4]
        self.rating = record[5]


def welcome_user(users):
    dm_channel = discord.bot_request("/users/@me/channels", "POST", json={"recipient_id": users.id})
    return discord.bot_request(
        f"/channels/{dm_channel['id']}/messages", "POST", json={"content": "Авторизация на сайте - прошла успешно!"}
    )


@app.context_processor
def any_data_processor():
    log_button_text = 'Логин'
    log_button_url = '/login'
    if discord.user_id is not None:
        users = discord.fetch_user()
        log_button_text = users.name
        log_button_url = '/me'
    log_button_text = f"{log_button_text}"
    return dict(logButtonText=log_button_text, logButtonUrl=log_button_url)


@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html")


@app.route("/login/")
def login():
    return discord.create_session(modified=True)


@app.route("/logout/")
def logout():
    discord.revoke()
    return redirect(url_for(".index"))


@app.route("/callback/")
def callback():
    discord.callback()
    users = discord.fetch_user()
    welcome_user(users)
    return redirect(url_for(".me"))


@app.errorhandler(Unauthorized)
def redirect_unauthorized():
    return redirect(url_for("login"))


@app.route("/me/")
@requires_authorization
def me():
    users = discord.fetch_user()
    client = IClient(users.id)
    if not client:
        info = {"Вы еще не зарегистрированы в системе"}
    else:
        info = {
            'Майнкрафт ник': client.nick,
            'Денег на счету': client.money,
            'Накопительных ячеек': client.deposit_box,
            'Денег на накопительном счету': client.deposit_money,
            'Дата регистрации': client.register_date,
            'Карта': client.card,
            'Роль': client.status
        }
    return render_template("profile.html", user=users, info=info)


@app.route("/members/")
def members():
    cur = mysql.connection.cursor()
    cur.execute("SELECT minecraftNick, card, status, id FROM user")
    info = cur.fetchall()
    cur.close()
    counteuser = len(info)
    return render_template("members.html", counteuser=counteuser, info=info)


@app.route('/profile/<int:ClientId>')
def profile(ClientId):
    client = IClient(ClientId)
    if client.check:
        users = {
            'id': f"{client.discord_id}",
            'name': f"{client.nick}",
            'avatar_url': f"https://minotar.net/armor/bust/{client.nick}/100.png"
        }
        info = {
            'Майнкрафт ник': client.nick,
            'Дата регистрации': client.register_date,
            'Карта': client.card,
            'Роль': client.status
        }
    else:
        users = {
            'id': " ",
            'name': ""
        }
        info = {"Пользователь не найден"}

    return render_template("profile.html", user=users, info=info)


@app.route("/sale/")
@app.route("/shops/")
@app.route("/shop/")
def shops():
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, rating, id, owner FROM shops")
    info = cur.fetchall()
    cur.close()
    counte = len(info)

    def getownername(ownerid):
        return IClient(ownerid).nick

    return render_template("shops.html", counte=counte, info=info, getownername=getownername)


@app.route('/shop/<int:ShopId>')
def shop(ShopId):
    shop = IShop(ShopId)
    if shop.check == False:
        return render_template('404.html'), 404
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT shop, id, name, discripiton, price, amount FROM itemstore WHERE shop = {ShopId}")
    item = cur.fetchall()
    cur.close()
    counte = len(item)
    return render_template("shop.html", shop=shop, counte=counte, item=item)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(host=settings['host'])
