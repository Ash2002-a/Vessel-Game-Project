from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    return render_template("pages/about.html")

@bp.route("/game")
def game():
	return render_template("pages/BloodVesselGame.html")

@bp.route("/consent")
def consent():
	return render_template("pages/consent.html")

@bp.route("/instructions")
def instructions():
	return render_template("pages/instructions.html")
	
@bp.route("/feedback")
def feedback():
	return render_template("pages/feedback.html")

@bp.route("/read_form", methods=['POST'])
def read_form():
	return render_template("pages/read_form.html")
