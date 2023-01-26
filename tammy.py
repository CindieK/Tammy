import os, time, bcrypt, datetime
import azure.cognitiveservices.speech as speechsdk
from flask_session import Session

from helpers import apology, login_required
from flask import Flask, session, flash, request, redirect, render_template
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# tammydb
from db import History, User, db
from sqlalchemy import desc

ALLOWED_EXTENSIONS = {'wav', 'mp3'}

# Configure application
app = Flask(__name__)
app.config['UPLOAD_FOLDER']='upload'

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# secret key is needed to use sessions to prevent people modifying the cookies
app.secret_key = 'eca9a759bc726c5ed407be8ac1162c8dda38fabae6618b618ebad62826780ad9'

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.add_url_rule(
    "/uploads/<name>", endpoint="download_file", build_only=True
)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS    

""" replace the extension of a given file """
def replace_extension(filename, new_extension):
    name, ext = filename.split(".")
    return name + "." + new_extension

date = datetime.datetime.today()

"""Show homepage, fix later"""
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # user_id = session["user_id"]
    return render_template("index.html")
    
# Show generated transcript
@app.route("/transcript", methods=["GET", "POST"])
@login_required
def transcript():  
    all_results = "No file selected"
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))

    if request.method == "POST":
        print("FORM DATA RECEIVED")

        if "file" not in request.files:
            flash('No file uploaded!')
            return redirect("/")

        file = request.files["file"]

        if file.filename == "":
            flash('No selected file!')
            return redirect("/")
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(full_file_path)
            audio_config = speechsdk.AudioConfig(filename = full_file_path) 
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            done = False

            def stop_cb(evt):
                print('SESSION STOPPED on {}'.format(evt))
                speech_recognizer.stop_continuous_recognition()
                nonlocal done
                done = True  

            all_results = []
            
            def handle_final_result(evt):
                all_results.append(evt.result.text) 
            
            def handle_cancellation(evt):
                print ("CANCELED {}".format(evt.result.text))
                print ("CANCELED {}".format(evt))
                print( evt.error_details)


            speech_recognizer.recognized.connect(handle_final_result) 
            speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt))) 
            speech_recognizer.recognized.connect(lambda evt: print('RECOGNIZED: {}'.format(evt.result.text)))
            speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
            speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
            speech_recognizer.canceled.connect(handle_cancellation)
            # stop continuous recognition on either session stopped or canceled events
            speech_recognizer.session_stopped.connect(stop_cb)
            speech_recognizer.canceled.connect(handle_cancellation) 
            
            speech_recognizer.start_continuous_recognition()

            while not done:
                time.sleep(.5)
            
            print("Printing all results:")
            print(all_results)

            newfile = replace_extension(filename, "txt")
            transcript = f'static/transcripts/{newfile}'

            with open(transcript,'w') as f:
                f.write('\n'.join(all_results))

            try:
                # session['user_id'] = user.id  
                history = History(user_id=session['user_id'], filename=filename, transcript=transcript, date=date)
                db.add(history)
                db.commit()
                return redirect('/history')
            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=}")
                return apology("Something went wrong!")

        else:
            print("Something went wrong w/ file")
        
    return render_template("history.html", all_results=all_results)

@app.route("/history", methods=["GET"])
@login_required
def history():

    history = db.query(History).filter_by(user_id = session["user_id"]).order_by(desc(History.date))
    return render_template("history.html", history=history)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if (request.method == "POST"):
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        if not username:
            return apology("Username is required!")
        elif not password:
            return apology("Password is required!")
        elif not confirmation:
            return apology("Password confirmation is required!")
        if password != confirmation:
            return apology("Passwords do not match!")

        # Hash a password for the first time, with a randomly-generated salt
        # hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        hash = generate_password_hash(password)

        try:
            newUser = User(username=username, password=hash)
            db.add(newUser)
            db.commit()
            return redirect('/login')
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            return apology("Username has already been registered!")

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        password = request.form.get('password')
        username = request.form.get('username')

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # symbols_user database for username
        user = db.query(User).filter_by(username=request.form.get('username')).first()
        # hash = generate_password_hash(password)

        if (user == None):
            return apology("Invalid username/password", 403)

        # Ensure username exists and password is correct
        if not check_password_hash(user.password, request.form.get("password")):
            return apology("Invalid password", 403)
        
        # makes more sense than storing just a bool
        session['user_id'] = user.id  
        return redirect('/')

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)