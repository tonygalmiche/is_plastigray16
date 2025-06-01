from odoo import http                     # type: ignore
from odoo.http import request             # type: ignore
from werkzeug.exceptions import NotFound  # type: ignore

class SignupDisabled(http.Controller):

    @http.route('/web/signup', type='http', auth='public', website=True)
    def disable_signup(self, **kwargs):
        # Option 1 : renvoyer une erreur 404
        raise NotFound()

        # Option 2 : rediriger vers la page de login
        # return request.redirect('/web/login')
