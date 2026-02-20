"""
FinWise Calculators — Flask application factory.
"""
from datetime import datetime, timezone
from flask import Flask, render_template, Response
from config import SITE_URL, SITE_NAME, SITEMAP_PAGES


def create_app():
    app = Flask(__name__)

    # ── Register blueprints ────────────────────────────────────────────────
    from calculators.mortgage import mortgage_bp
    from calculators.investment import investment_bp
    from calculators.debt import debt_bp
    from calculators.tax import tax_bp
    from calculators.specialized import specialized_bp

    app.register_blueprint(mortgage_bp)
    app.register_blueprint(investment_bp)
    app.register_blueprint(debt_bp)
    app.register_blueprint(tax_bp)
    app.register_blueprint(specialized_bp)

    # ── Homepage ───────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    # ── Sitemap ────────────────────────────────────────────────────────────
    @app.route("/sitemap.xml")
    def sitemap():
        now = datetime.now(timezone.utc)
        xml = render_template(
            "sitemap.xml",
            pages=SITEMAP_PAGES,
            base_url=SITE_URL,
            now=now,
        )
        return Response(xml, mimetype="application/xml")

    # ── robots.txt ─────────────────────────────────────────────────────────
    @app.route("/robots.txt")
    def robots():
        content = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
        return Response(content, mimetype="text/plain")

    # ── Global template context ────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {"site_name": SITE_NAME, "site_url": SITE_URL}

    # ── Custom error pages ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
