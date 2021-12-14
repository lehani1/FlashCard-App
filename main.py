from flask import Flask,render_template,url_for,redirect,request,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager,login_user,login_required, logout_user, current_user

from flask_restful import Api, Resource, reqparse
import random as rd
from time import time

app = Flask(__name__)
api = Api(app)
log = {}

#------------------------DATABASE INITIALISATION----------------------------
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///testdbtemp.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'
#----------------------------------------------------------------------------

#----------------------------------------Login manager----------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
#---------------------------------------------------------------------------------------------

class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key = True,autoincrement = True,nullable = False)
    username = db.Column(db.String(64), unique = True,index = True, nullable = False)
    password = db.Column(db.String(64), nullable = False)


class Card(db.Model):
    id = db.Column(db.Integer, primary_key = True, unique = True,autoincrement = True,nullable = False)
    front = db.Column(db.String(25),unique = True)
    back = db.Column(db.String(64), nullable = False)


class Deck(db.Model):
    id = db.Column(db.Integer,primary_key = True,autoincrement = True,nullable = False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'),index = True)
    deck_name = db.Column(db.String(64), index = True, nullable = False)
    user_score = db.Column(db.Integer,nullable = True)
class cdtable(db.Model):
    id = db.Column(db.Integer, primary_key = True,autoincrement = True,nullable = False)
    deck_id = db.Column(db.Integer,db.ForeignKey('deck.id'),nullable = False)
    card_id = db.Column(db.Integer,db.ForeignKey('card.id'),nullable = False)


#----------------------------------API METHODS----------------------------------------
def get_card(card_id):
    card = Card.query.filter_by(id = card_id).first()
    return card

class CardAPI(Resource):
    def get(self,card_id):
        card = get_card(card_id)
        if card != None:
            out = {'front': card.front, 'back':card.back }
            return out,200
        else:
            return {'message' : "card not present in database"},404
    def post(self):
        card_parser = reqparse.RequestParser()
        card_parser.add_argument('front', type=str)
        card_parser.add_argument('back', type=str)
        args = card_parser.parse_args()
        card_args = card_parser.parse_args()
        front = card_args['front']
        back = card_args['back']
        card_existing = Card.query.filter_by(front = front,back = back).first()
        if card_existing == None:

            new_card = Card(front = front, back = back)
            db.session.add(new_card)
            db.session.commit()
            card = Card.query.filter_by(front = front, back = back).first()
            return {"card id":card.id,"front": card.front, "back": card.back},200
        return "Card already present",409

    def put(self,card_id):
        card_parser = reqparse.RequestParser()
        card_parser.add_argument('front', type=str)
        card_parser.add_argument('back', type=str)
        card = get_card(card_id)
        if card != None:
            card_args = card_parser.parse_args()
            front = card_args['front']
            back = card_args['back']
            
            card.front = front
            db.session.commit()
            card.back =back
            db.session.commit()
            return "succesfully updated",200
        else:
            return "",404

    def delete(self,card_id):
        card = Card.query.filter_by(id = card_id).first()
        if card != None:
            #delete the card from all decks
            q = cdtable.query.filter_by(card_id = card_id).all()
            decks = []
            for x in q:
                db.session.delete(x)
                db.session.commit()

            #now finally removing the card
            db.session.delete(card)
            db.session.commit()
            return 200

        else:
            return {'message' : "card not present in database"},404


class DeckAPI(Resource):
    def post(self,username):
        user = User.query.filter_by(username = username).first()
        if user != None:
            deck_parser = reqparse.RequestParser()
            deck_parser.add_argument('deck_name', type=str)
            args = deck_parser.parse_args()
            deck_name = args['deck_name']
            check_deck = Deck.query.filter_by(deck_name = deck_name).first()
            if check_deck == None:
                new_deck = Deck(owner_id = user.id, deck_name = deck_name)
                db.session.add(new_deck)
                db.session.commit()
                return "Deck added succesfully"
            else:
                return {'message':'Deck already present'}, 409
        else:
            return {'message':'user not present' },409


    def get(self, username):
        user = User.query.filter_by(username = username).first()
        if user != None:
            decks = Deck.query.all()
            if decks != None:

                out = []
                for deck in decks:
                    temp = {'deck_id':deck.id, 'deck name': deck.deck_name, 'User score in this deck': deck.user_score}
                    out.append(temp)
                return out,200
            else:
                return {'message':'Deck not present'}, 409
        else:
            return {'message':'user not present' },409

    def put(self, username,card_id,flag):
        user = User.query.filter_by(username = username).first()
        if user != None:
            check_deck = Deck.query.filter_by(id = deck_id).first()
            if check_deck != None:
                if flag == 0:
                    pass    #Add card
                    
                if flag == 1:
                    #delete card
                    entry = cdtable.query.filter_by(card_id = card_id,deck_id = deck_id).first()
                    if entry != None:
                        db.session.delete(entry)
                        db.session.commit()
                        return "",200
                    else:
                        return {'message':'Card not present in deck'}, 400

            else:
                return {'message':'Deck not present'}, 400

        else:
            return {'message':'user not present' },400


    def delete(self, username,deck_name):
        user = User.query.filter_by(username = username).first()
        if user != None:
            deck = Deck.query.filter_by(deck_name = deck_name).first()
            if deck:
                db.session.delete(deck)
                db.session.commit()
                return "Succesfully Deleted",200
            else:
                return {'message':'Deck not present'}, 404
        else:
            return {'message':'Invalid username or User not present' },404
#----------------------------------------Routes----------------------------------------
#GAME ROUTES
last_visited = []


def update_user_score(deck_id,new_score):
    user = current_user
    deck = Deck.query.filter_by(id = deck_id,owner_id = user.id).first() 
    old_score = deck.user_score
    if old_score != None:
        deck.user_score = old_score + new_score
        db.session.commit()
    if old_score == None:
        deck.user_score = new_score
        db.session.commit()

def get_user_score(deck_id):
    user = current_user
    deck = Deck.query.filter_by(id = deck_id,owner_id = user.id).first()
    score = deck.user_score
    return score

@login_required
def get_deck_cards(deck_id):
    cards = []
    q = cdtable.query.filter_by(deck_id = deck_id).all()
    card_id_list = [x.card_id for x in q]
    for x in card_id_list:
        card = Card.query.filter_by(id = x).first()
        cards.append(card)
    return cards



@app.route("/play/<int:deck_id>/rules")
@login_required
def play_rules(deck_id):
    return render_template('rules.html', deck_id = deck_id)



@app.route('/play/<int:deck_id>/game',methods =["GET","POST"])
@login_required
def play_game(deck_id):
    if request.method == 'POST':
        score = 0
        radio = request.form['radios']
        radio2 = request.form['radios2']
        if radio == 'correct':
            score += 4
            score += int(radio2)
        update_user_score(deck_id,score)


    cards = get_deck_cards(deck_id)
    k = rd.randint(0,len(cards)-1)
    card = cards[k]
    j = rd.randint(0,len(cards)-1)
    while True:
        if j!=k:
            break
        else:
            j = rd.randint(0,len(cards)-1)
    wrong_card = cards[j]
    return render_template('game.html', deck_id = deck_id, card = card, wrong_card = wrong_card)


@app.route('/play')
@login_required
def play_choose_deck():
    user = current_user
    q = Deck.query.filter_by(owner_id = user.id).all()
    decks = []
    for x in q:
        decks.append(x)

    if len(decks)==0:
        return render_template('play.html',flag = 0, user_id = user.id)

    return render_template('play.html', flag = 1,decks = decks)



#--------------------------------------------------------------------------------------
#CRUD AND LOGIN STUFF


def is_card_already_present(front,back):
    card = Card.query.filter_by(front = front,back = back).first()
    if card == None:
        return False
    else:
        return True
def insert_card_in_card_table(front,back):
    new_card = Card(front=front,back = back)
    db.session.add(new_card)
    db.session.commit()
def insert_card_in_deck(deck_id,front,back):
    card_exists = Card.query.filter_by(front = front,back = back).first()
    #checking if card exists in card table or not, if not adding it to deck
    if card_exists == None:
        insert_card_in_card_table(front,back)
    card = Card.query.filter_by(front = front,back = back).first()
    #checking if card is already present in user deck
    card_in_deck = cdtable.query.filter_by(deck_id = deck_id,card_id = card.id).first()

    if card_in_deck == None:
        new_entry = cdtable(deck_id = deck_id,card_id = card.id)
        db.session.add(new_entry)
        db.session.commit()
    else:
        flash("Card already present in deck")

def query_all_cards():
    q = Card.query.all()
    cards = []
    for x in q:
        cards.append(x)
    return cards
#--------------------ROUTING-----------------------------------------------

@app.route('/cards', methods = ['GET','POST'])
@login_required
def shared_cards():
    cards = query_all_cards()
    return render_template('cards.html', cards = cards)

@app.route('/cards/update/<int:card_id>', methods = ['GET','POST'])
@login_required
def update_shared_card(card_id):
    if request.method == 'POST':
        front = request.form['card_front']
        back = request.form['card_back']
        card = get_card(card_id)
        card.front = front
        db.session.commit()
        card.back = back
        db.session.commit()
        return redirect(url_for('shared_cards'))
    return render_template('card_update.html',card_id = card_id)
@app.route('/cards/delete/<int:card_id>', methods = ['GET','POST'])
@login_required
def delete_shared_card(card_id):
    #delete from all decks
    entries = cdtable.query.filter_by(card_id = card_id).all()
    for entry in entries:
        db.session.delete(entry)
        db.session.commit()

    #delete from the card database
    card = Card.query.filter_by(id = card_id).first()
    db.session.delete(card)
    db.session.commit()
    return redirect(url_for('shared_cards'))

@app.route('/delete/<int:user_id>/deck/<int:deck_id>', methods = ['GET','POST'])
@login_required
def delete_deck(deck_id,user_id):
    #delete all entries from cdtable and then delete the deck from Deck table
    entries = cdtable.query.filter_by(deck_id = deck_id).all()
    for entry in entries:
        db.session.delete(entry)
        db.session.commit()
    #now deleting the deck
    deck = Deck.query.filter_by(id = deck_id).first()
    db.session.delete(deck)
    db.sesion.commit()
    return redirect(url_for('user_deck'))

@app.route('/create/<int:user_id>/deck', methods = ['GET','POST'])
@login_required
def create_deck(user_id):
    user = current_user
    if request.method == "POST":
        deck_name = request.form['deck_name']
        new_deck = Deck(deck_name = deck_name,owner_id = user_id)
        db.session.add(new_deck)
        db.session.commit()
        return redirect(url_for('user_deck'))
    return render_template('crud.html',flag = 2,user_id = user.id)

@app.route('/decks/<int:deck_id>/add_existing_card/<int:card_id>', methods = ['GET','POST'])
@login_required
def add_existing_card_to_deck(deck_id,card_id):
    card = Card.query.filter_by(id = card_id).first()
    entry = cdtable.query.filter_by(deck_id = deck_id, card_id = card_id).first()
    if entry == None:
        new_entry = cdtable(deck_id = deck_id,card_id = card_id)
        db.session.add(new_entry)
        db.session.commit()
    else:
        flash("Card already present in deck")
    return redirect(url_for('add_card',deck_id = deck_id))

@app.route('/decks/<int:deck_id>/add_card', methods = ['GET','POST'])
@login_required
def add_card(deck_id):
    if request.method == "POST":
        front = request.form['card_front']
        back = request.form['card_back']
        insert_card_in_deck(deck_id,front,back)
        flash('Card added')
    cards = query_all_cards()
    return render_template('crud.html', flag = 0,deck_id = deck_id, cards = cards)

@app.route('/decks/<int:deck_id>/delete/<int:card_id>', methods = ['GET','POST'])
@login_required
def delete_card(deck_id,card_id):
    entry = cdtable.query.filter_by(deck_id = deck_id,card_id = card_id).first()
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('show_deck',deck_id = deck_id))

@app.route('/decks/<int:deck_id>/update/<int:card_id>', methods = ['GET','POST'])
@login_required
def update_card(deck_id,card_id):
    if request.method == 'GET':
        return render_template('crud.html', flag = 1,deck_id = deck_id,card_id = card_id)
    if request.method == 'POST':
        front = request.form['card_front']
        back = request.form['card_back']
        card = Card.query.filter_by(id = card_id).first()
        card.front = front
        db.session.commit()
        card.back = back
        db.session.commit()
        return redirect(url_for('show_deck',deck_id = deck_id))


@app.route('/decks/<int:deck_id>')
@login_required
def show_deck(deck_id):
    cards = cdtable.query.filter_by(deck_id = deck_id).all()
    card_id_list = [x.card_id for x in cards]
    print(cards)
    cards = []
    for x in card_id_list:
        q = Card.query.filter_by(id = x).first()
        cards.append(q)
    print(cards)
    length = len(card_id_list)
    user = current_user
    return render_template('decks.html', flag = 2,cards = cards,deck_id = deck_id,user_id = user.id, length = length)


@app.route('/decks', methods = ['GET','POST'])
@login_required
def user_deck():
    user = current_user
    deck_list = []
    decks = Deck.query.filter_by(owner_id = user.id).all()
    for x in decks:
        deck_list.append(x)
    length = len(deck_list)
    if len(deck_list) == 0:
        return render_template('decks.html',flag = 0,user_id = user.id)
    else:
        return render_template('decks.html',flag = 1, length = length,decks = deck_list, user_id = user.id)


@app.route('/logout', methods = ['GET','POST'])
@login_required
def logout():
    logout_user()
    flash("Yor have succesfully logged out!")
    return redirect(url_for('login'))

def get_log(log):
    return log

@app.route('/dashboard', methods = ['GET','POST'])
@login_required
def dashboard():
    user = current_user
    decks = Deck.query.filter_by(owner_id = user.id)
    return render_template('dashboard.html', decks = decks)

@app.route('/login',methods = ['GET','POST'])
def login(): 
    if request.method =='POST':
        uname = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username = uname).first()
        if user!=None and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Wrong credentials! Please try again!")
    return render_template('login.html')

@app.route('/')
def index():
    return render_template('index.html')

api.add_resource(CardAPI, '/api/card/<int:card_id>',"/api/card")
api.add_resource(DeckAPI, "/api/deck/<string:username>/delete/<string:deck_name>","/api/<string:username>/decks")
#--------------------ROUTING ENDS-------------------------------------------


if __name__ == '__main__':
    app.run(debug = True)
#
#
#
#
#
#
#
#
