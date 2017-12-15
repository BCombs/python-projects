from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from datetime import datetime

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    stocks = db.execute("SELECT * FROM owned JOIN stocks WHERE owned.stock_id = stocks.stock_id AND user_id = :user_id AND shares > 0 ORDER BY symbol", 
        user_id=session["user_id"])
    user = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    cash = user[0]["cash"]
    
    # store the sum of the current stock prices
    sum = 0
    
    # get the current stock price and add it to the dictionary. Add to sum the current price of the stocks * number of shares owned
    for stock in stocks:
        price = lookup(stock["symbol"])
        stock["currentPrice"] = price["price"]
        sum += price["price"] * stock["shares"]
    
    # grand total of cash + stocks
    total = sum + cash
        
    return render_template("index.html", stocks = stocks, cash=cash, total=total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please enter stock symbol")
        elif not request.form.get("amount"):
            return apology("Please enter amount to purchase")
        elif int(request.form.get("amount")) <= 0:
            return apology("Please enter a value greater than 0")
            
        # lookup the stock symbol entered
        stock = lookup(request.form.get("symbol"))
        
        # if lookup didn't find the stock
        if stock == None:
            return apology("Invalid stock symbol")
        else:
            name = stock["name"]
            price = stock["price"]
            symbol = stock["symbol"]
            
        # the amount of stock the user wants to purchase
        amount = int(request.form.get("amount"))
        
        # total price of the purchase
        total = price * amount
        
        # get the amount of money the user has
        user = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        
        # if there was an error accessing user
        if not user:
            return apology("Error accessing account")
        
        cash = user[0]["cash"]
        
        # make sure the user has enough money to complete the purchase
        if total > cash:
            return apology("Not enough funds to complete transaction")
        else:
            # check if the stock already exists
            result = db.execute("SELECT * FROM stocks WHERE symbol = :symbol", symbol=symbol)
            
            # if the stock isnt in the stocks database, add it
            if not result:
                result = db.execute("INSERT INTO stocks (symbol, name) VALUES (:symbol, :name)", 
                    symbol=symbol, name=name)
            
            # get the stock
            result = db.execute("SELECT * FROM stocks WHERE symbol = :symbol", symbol=symbol)
            
            # get the ID of the stock
            stock_id = result[0]["stock_id"]
            
            # deduct from the users account
            result = db.execute("UPDATE users SET cash = cash - :total WHERE id = :id", id=session["user_id"], total=total)
            
             # if there was an error deducting from account
            if not result:
                return apology("Could not complete purchase")
            
            # insert purchase into the database
            result = db.execute("INSERT INTO purchases (user_id, shares, price, date, stock_id, t_type) VALUES (:user_id, :shares, :price, :date, :stock_id, :t_type)", 
                user_id=session["user_id"], shares=amount, price=price, date=datetime.now().strftime('%m-%d-%Y %H:%M:%S'), stock_id=stock_id, t_type="Purchased")
                
            # if there was a problem
            if not result:
                return apology("Could not complete purchase")
            
            # see if the user owns shares of that stock already
            result = db.execute("SELECT stock_id FROM owned WHERE stock_id = :stock_id AND user_id = :user_id", 
                stock_id=stock_id, user_id=session["user_id"])
            
            if not result:
                # the user doesn't own any shares of the stock already, insert it to owned
                result = db.execute("INSERT INTO owned (user_id, stock_id, shares) VALUES (:user_id, :stock_id, :shares)", 
                    user_id=session["user_id"], stock_id=stock_id, shares=amount)
                
                # if there was a problem inserting
                if not result:
                    return apology("Error updating owned shares")
            else:
                # the user already owns shares, update the amount
                result = db.execute("UPDATE owned SET shares = shares + :shares WHERE user_id = :user_id AND stock_id = :stock_id", 
                    user_id=session["user_id"], shares=amount, stock_id=stock_id)
                
                # if there was a problem updating
                if not result:
                    return apology("Error updating already owned shares")

            # go to the index page
            return redirect(url_for("index"))
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    stocks = db.execute("SELECT * FROM purchases JOIN stocks WHERE purchases.stock_id = stocks.stock_id AND user_id = :user_id ORDER BY date DESC", 
        user_id=session["user_id"])
    return render_template("history.html", stocks = stocks)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""
    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # if a symbol was entered via form
    if request.method == "POST":
        
        # if the symbol field is blank return apology
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol")
        
        # dictionary to store our quote
        quote = lookup(request.form.get("symbol"))
        
        # if lookup() returns None, the stock wasn't found
        if quote == None:
            return apology("Invalid stock symbol")
        # it was found
        else:
            symbol = quote["symbol"]
            name = quote["name"]
            price = usd(quote["price"])
            
            # Show the user the quote
            return render_template("quoted.html", symbol=symbol, name=name,price=price)
        
    # User reached quote page via link or redirect
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        
        # ensure a username was submitted
        if not request.form.get("username"):
            return apology("Must provide a username")
        
        # ensure the password and verify passwords are not empty
        elif not request.form.get("password") or not request.form.get("vpassword"):
            return apology("Must enter and verify a password")
            
        # if password and vpassword don't match
        elif request.form.get("password") != request.form.get("vpassword"):
            return apology("Passwords do not match")
            
        # hash the password
        hash = pwd_context.hash(request.form.get("password"))
        
        # insert the user into the database
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash=hash)
        
        # if result is false, username already exists
        if not result:
            return apology("Username already exists")
        # success! log them in
        else:
            # query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
            
            # start their session
            session["user_id"] = rows[0]["id"]
            
            # redirect user to home page
            return redirect(url_for("index"))
        
    # if request was reached via GET        
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol")
        elif not request.form.get("amount"):
            return apology("Please enter amount to sell")
        elif int(request.form.get("amount")) < 1:
            return apology("Invalid amount specified")
        
        # the symbol entered
        symbol = request.form.get("symbol")
        
        # the amount of shares the user wants to sell    
        amount = int(request.form.get("amount"))
        
        # look up the current price of the stock to sell   
        stock = lookup(symbol)
        if stock == None:
            return apology("Invalid stock symbol")

        price = stock["price"]
        
        # get the stock ID of the current stock
        result = db.execute("SELECT stock_id FROM stocks WHERE symbol = :symbol", symbol=symbol)
        if not result:
            return apology("Could not get current stock ID")
        
        stock_id = int(result[0]["stock_id"])
        
        # make sure the user actually owns shares of the stock they entered
        isOwned = db.execute("SELECT shares FROM owned JOIN stocks WHERE owned.stock_id = stocks.stock_id AND user_id = :user_id", 
            user_id=session["user_id"])
        
        # if the user didn't own any shares return apology
        if not isOwned:
            return apology("You don't own any shares of that stock")
        else:
            # the amount of shares owned by the user
            amountOwned = int(isOwned[0]["shares"])
            # user owned shares, make sure they own the amount they are trying to sell
            if amount > amountOwned:
                return apology("You don't own enough shares")
            else:
                # total value of sale
                total = amount * price
                
                # sell the shares
                result = db.execute("UPDATE owned SET shares = shares - :amount WHERE stock_id = :stock_id AND user_id = :user_id", 
                    amount=amount, stock_id=stock_id, user_id=session["user_id"])
                if not result:
                    return apology("Couldn't complete transaction")
                
                # update users cash
                result = db.execute("UPDATE users SET cash = cash + :total WHERE id = :user_id", 
                    total=total, user_id=session["user_id"])
                if not result:
                    return apology("Couldn't update cash")
                
                # insert the sale into purchases(history)
                result = db.execute("INSERT INTO purchases (user_id, shares, price, date, stock_id, t_type) VALUES (:user_id, :shares, :price, :date, :stock_id, :t_type)", 
                    user_id=session["user_id"], shares=amount, price=price, date=datetime.now().strftime('%m-%d-%Y %H:%M:%S'), stock_id=stock_id, t_type="Sold")
                
                # send the user back to the sell.html
                return redirect(url_for("sell"))
    else:
        stocks = db.execute("SELECT * FROM owned JOIN stocks WHERE owned.stock_id = stocks.stock_id AND user_id = :user_id AND shares > 0 ORDER BY symbol", 
            user_id=session["user_id"])
        
        user = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash = user[0]["cash"]
    
        # store the sum of the current stock prices
        sum = 0
        
        # get the current stock price and add it to the dictionary. Add to sum the current price of the stocks * number of shares owned
        for stock in stocks:
            price = lookup(stock["symbol"])
            stock["currentPrice"] = price["price"]
            sum += price["price"] * stock["shares"]

        return render_template("sell.html", stocks=stocks, cash=cash)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Update account settings."""
    if request.method == "POST":
        if not request.form.get("password"):
            return apology("Please enter current password")
        elif not request.form.get("new_password"):
            return apology("Please enter a new password")
        elif not request.form.get("vpassword"):
            return apology("Please verify new password")
            
        # hash the new password the user entered
        hash = pwd_context.hash(request.form.get("password"))
        
        # get the current user
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        
        # ensure password is correct
        if len(user) != 1 or not pwd_context.verify(request.form.get("password"), user[0]["hash"]):
            return apology("invalid password")
        else:
            # make sure the new password and verification match
            if request.form.get("new_password") != request.form.get("vpassword"):
                return apology("New passwords do not match")
            else:
                # hash the new password
                hash = pwd_context.hash(request.form.get("new_password"))
                # update the password in the database
                result = db.execute("UPDATE users SET hash = :hash WHERE id = :user_id", user_id=session["user_id"], hash=hash)
                if not result:
                    return apology("Error updating password")
                
                # success, return to index
                return redirect(url_for("index"))
    else:
        return render_template("settings.html")